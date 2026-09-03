from datetime import datetime
from flask import abort
from sqlalchemy import text
from app import db
from app.utils.grew_utils import grew_request
from conllup.conllup import sentenceConllToJson
from .model import StagedTree


VALIDATED_TREE_USER_ID = 'validated'
PINNED_BY_GITHUB_REFERENCE = 'github_reference'


class StagingService:

    @staticmethod
    def _get_pinned_user_column() -> str:
        try:
            rows = db.session.execute(text("PRAGMA table_info(pinned_trees)")).fetchall()
        except Exception:
            rows = []

        if not rows:
            db.session.execute(text(
                """
                CREATE TABLE IF NOT EXISTS pinned_trees (
                    id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    sample_id VARCHAR(255) NOT NULL,
                    sent_id VARCHAR(255) NOT NULL,
                    tree_user_id VARCHAR(255) NOT NULL,
                    pinned_by VARCHAR(255) NOT NULL,
                    pinned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(id),
                    UNIQUE(project_id, sample_id, sent_id, tree_user_id, pinned_by)
                )
                """
            ))
            db.session.commit()
            return 'tree_user_id'

        columns = {row[1] for row in rows}
        if 'tree_user_id' in columns:
            return 'tree_user_id'
        if 'user_id' in columns:
            return 'user_id'

        db.session.execute(text("ALTER TABLE pinned_trees ADD COLUMN tree_user_id VARCHAR(255)"))
        db.session.commit()
        return 'tree_user_id'

    @staticmethod
    def _same_tree_content(conll_a: str, conll_b: str) -> bool:
        try:
            tree_a = sentenceConllToJson(conll_a).get('treeJson', {})
            tree_b = sentenceConllToJson(conll_b).get('treeJson', {})
            return tree_a == tree_b
        except Exception:
            return False

    @staticmethod
    def upsert_pin_if_matches_reference(
        project_name: str,
        project_id: int,
        sample_id: str,
        sent_id: str,
        tree_user_id: str,
    ) -> bool:
        """Pin a user tree when it is identical to the GitHub reference tree for that sentence."""
        if tree_user_id == VALIDATED_TREE_USER_ID:
            return False

        reply = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_id},
        )
        sample_data = reply.get("data", {})
        sentence_data = sample_data.get(sent_id, {})
        if not isinstance(sentence_data, dict):
            return False

        reference_conll = sentence_data.get(VALIDATED_TREE_USER_ID)
        user_conll = sentence_data.get(tree_user_id)

        user_col = StagingService._get_pinned_user_column()
        existing_pin = db.session.execute(
            text(
                f"SELECT id FROM pinned_trees WHERE project_id = :project_id AND sample_id = :sample_id "
                f"AND sent_id = :sent_id AND {user_col} = :tree_user_id AND pinned_by = :pinned_by"
            ),
            {
                'project_id': project_id,
                'sample_id': sample_id,
                'sent_id': sent_id,
                'tree_user_id': tree_user_id,
                'pinned_by': PINNED_BY_GITHUB_REFERENCE,
            },
        ).fetchone()

        if not reference_conll or not user_conll or not StagingService._same_tree_content(user_conll, reference_conll):
            if existing_pin:
                db.session.execute(
                    text("DELETE FROM pinned_trees WHERE id = :id"),
                    {'id': existing_pin[0]},
                )
                db.session.commit()
            return False

        if existing_pin:
            db.session.execute(
                text("UPDATE pinned_trees SET pinned_at = :pinned_at WHERE id = :id"),
                {'pinned_at': datetime.utcnow(), 'id': existing_pin[0]},
            )
        else:
            db.session.execute(
                text(
                    f"INSERT INTO pinned_trees (project_id, sample_id, sent_id, {user_col}, pinned_by, pinned_at) "
                    "VALUES (:project_id, :sample_id, :sent_id, :tree_user_id, :pinned_by, :pinned_at)"
                ),
                {
                    'project_id': project_id,
                    'sample_id': sample_id,
                    'sent_id': sent_id,
                    'tree_user_id': tree_user_id,
                    'pinned_by': PINNED_BY_GITHUB_REFERENCE,
                    'pinned_at': datetime.utcnow(),
                },
            )

        db.session.commit()
        return True

    @staticmethod
    def get_pinned_status_by_sample(project_id: int, sample_id: str) -> dict:
        user_col = StagingService._get_pinned_user_column()
        pinned_rows = db.session.execute(
            text(
                f"SELECT sent_id, {user_col} AS tree_user_id, pinned_at FROM pinned_trees "
                "WHERE project_id = :project_id AND sample_id = :sample_id AND pinned_by = :pinned_by"
            ),
            {
                'project_id': project_id,
                'sample_id': sample_id,
                'pinned_by': PINNED_BY_GITHUB_REFERENCE,
            },
        ).fetchall()

        result = {}
        for row in pinned_rows:
            sent_id = row[0]
            tree_user_id = row[1]
            pinned_at = row[2]

            if sent_id not in result:
                result[sent_id] = {}
            result[sent_id][tree_user_id] = {
                'status': 'pinned',
                'staged_by': 'github',
                'staged_at': pinned_at.isoformat() if hasattr(pinned_at, 'isoformat') else (str(pinned_at) if pinned_at else None),
            }
        return result

    @staticmethod
    def clear_all_pins(project_id: int, sample_id: str):
        StagingService._get_pinned_user_column()
        db.session.execute(
            text("DELETE FROM pinned_trees WHERE project_id = :project_id AND sample_id = :sample_id"),
            {'project_id': project_id, 'sample_id': sample_id},
        )
        db.session.commit()

    @staticmethod
    def clear_pins_for_sentence(project_id: int, sample_id: str, sent_id: str):
        StagingService._get_pinned_user_column()
        db.session.execute(
            text("DELETE FROM pinned_trees WHERE project_id = :project_id AND sample_id = :sample_id AND sent_id = :sent_id"),
            {'project_id': project_id, 'sample_id': sample_id, 'sent_id': sent_id},
        )
        db.session.commit()

    @staticmethod
    def stage(project_id: int, sample_id: str, sent_id: str, tree_user_id: str, staging_user_id: str):
        """
        Stage a tree for GitHub push.
            
        409: If already staged by a different admin
        """
        # Only one admin can stage a sentence at a time
        active_staging = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            sent_id=sent_id,
            status='staged'
        ).first()

        if active_staging and (
            active_staging.tree_user_id != tree_user_id
            or active_staging.staging_user_id != staging_user_id
        ):
            abort(
                409,
                f"This sentence is already staged by {active_staging.staging_user_id}. "
                f"You must unstage {active_staging.staging_user_id}'s tree before staging yours.",
            )

        existing = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            sent_id=sent_id,
            tree_user_id=tree_user_id
        ).first()
        if existing:
            existing.status = 'staged'
            existing.staging_user_id = staging_user_id
            existing.staged_at = datetime.utcnow()
        else:
            staged_tree = StagedTree(
                project_id=project_id,
                sample_id=sample_id,
                sent_id=sent_id,
                tree_user_id=tree_user_id,
                staging_user_id=staging_user_id,
                staged_at=datetime.utcnow(),
                status='staged'
            )
            db.session.add(staged_tree)
        
        db.session.commit()

    @staticmethod
    def restore_after_reset(project_id: int, sample_id: str, reset_targets: dict):
        staged_trees = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
        ).all()

        for tree in staged_trees:
            if tree.tree_user_id == VALIDATED_TREE_USER_ID:
                continue

            target_user_id = reset_targets.get(tree.sent_id)
            if target_user_id and tree.tree_user_id == target_user_id:
                tree.status = 'pushed'
                if tree.pushed_at is None:
                    tree.pushed_at = tree.staged_at or datetime.utcnow()
                if tree.pushed_by is None:
                    tree.pushed_by = tree.staging_user_id
                continue

            if tree.status == 'staged' or target_user_id == tree.tree_user_id:
                tree.status = 'unstaged'
                tree.pushed_at = None
                tree.pushed_by = None

        db.session.commit()

    @staticmethod
    @staticmethod
    def stage_sample(project_name: str, project_id: int, sample_id: str, tree_user_id: str, staging_user_id: str):
        """Stage every tree in a sample for the given user id."""
        reply = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_id},
        )
        sample_data = reply.get("data", {})

        for sent_id, sentence_data in sample_data.items():
            if isinstance(sentence_data, dict) and "conlls" in sentence_data:
                user_ids = sentence_data.get("conlls", {}).keys()
            elif isinstance(sentence_data, dict):
                user_ids = sentence_data.keys()
            else:
                continue

            for user_id in user_ids:
                if tree_user_id and user_id != tree_user_id:
                    continue
                StagingService.stage(project_id, sample_id, sent_id, user_id, staging_user_id)

    @staticmethod
    def unstage(project_id: int, sample_id: str, sent_id: str, tree_user_id: str):
        """
        Remove staging flag from a tree.
        """
        staged_tree = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            sent_id=sent_id,
            tree_user_id=tree_user_id
        ).first()
        
        if staged_tree:
            staged_tree.status = 'unstaged'
            db.session.commit()

    @staticmethod
    def is_staged(project_id: int, sample_id: str, sent_id: str, tree_user_id: str) -> dict:
        """
        Check if a tree is staged.
        """
        staged_tree = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            sent_id=sent_id,
            tree_user_id=tree_user_id,
            status='staged'
        ).first()
        
        if staged_tree:
            return {
                'staged_by': staged_tree.staging_user_id,
                'staged_at': staged_tree.staged_at.isoformat() if staged_tree.staged_at else None,
                'tree_user_id': staged_tree.tree_user_id
            }
        return {}

    @staticmethod
    def get_staged_status_by_sample(project_id: int, sample_id: str) -> dict:
        """
        Get staging status for all trees in a sample.
        """
        staged_trees = (
            StagedTree.query.filter_by(
                project_id=project_id,
                sample_id=sample_id
            )
            .filter(StagedTree.status.in_(['staged', 'pushed']))
            .all()
        )
        
        result = {}
        for tree in staged_trees:
            if tree.tree_user_id == VALIDATED_TREE_USER_ID:
                continue

            if tree.sent_id not in result:
                result[tree.sent_id] = {}

            result[tree.sent_id][tree.tree_user_id] = {
                'status': tree.status,
                'staged_by': tree.staging_user_id,
                'staged_at': tree.staged_at.isoformat() if tree.staged_at else None,
                'pushed_by': tree.pushed_by,
                'pushed_at': tree.pushed_at.isoformat() if tree.pushed_at else None
            }
        
        return result

    @staticmethod
    def mark_as_pushed(project_id: int, sample_id: str, pushed_by: str, sent_id: str = None, tree_user_id: str = None):
        """
        Mark staged trees as pushed after GitHub push.
        """
        query = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            status='staged'
        )
        
        if sent_id:
            query = query.filter_by(sent_id=sent_id)
        if tree_user_id:
            query = query.filter_by(tree_user_id=tree_user_id)

        staged_trees = query.all()
        for tree in staged_trees:
            previous_pushed_trees = StagedTree.query.filter_by(
                project_id=project_id,
                sample_id=sample_id,
                sent_id=tree.sent_id,
                status='pushed'
            ).all()

            for previous_tree in previous_pushed_trees:
                if previous_tree.tree_user_id == tree.tree_user_id:
                    continue
                previous_tree.status = 'unstaged'
                previous_tree.pushed_at = None
                previous_tree.pushed_by = None

            tree.status = 'pushed'
            tree.pushed_at = datetime.utcnow()
            tree.pushed_by = pushed_by
        
        db.session.commit()

    @staticmethod
    def clear_all_staging(project_id: int, sample_id: str):
        """
        Cleanup all staging for a sample.
        """
        staged_trees = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id
        ).all()
        
        for tree in staged_trees:
            db.session.delete(tree)
        
        db.session.commit()
