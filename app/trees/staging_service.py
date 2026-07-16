from datetime import datetime
from flask import abort
from app import db
from .model import StagedTree


class StagingService:

    @staticmethod
    def stage(project_id: int, sample_id: str, sent_id: str, tree_user_id: str, staging_user_id: str):
        """
        Stage a tree for GitHub push.
            
        409: If already staged by a different admin
        """
        # Check if already staged by someone else
        existing = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            sent_id=sent_id,
            tree_user_id=tree_user_id
        ).first()
        
        if existing and existing.status == 'staged' and existing.staging_user_id != staging_user_id:
            abort(409, f"Already staged by {existing.staging_user_id}")
        
        # Create staging
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
        staged_trees = StagedTree.query.filter_by(
            project_id=project_id,
            sample_id=sample_id,
            status='staged'
        ).all()
        
        result = {}
        for tree in staged_trees:
            if tree.sent_id not in result:
                result[tree.sent_id] = {}
            
            result[tree.sent_id][tree.tree_user_id] = {
                'staged_by': tree.staging_user_id,
                'staged_at': tree.staged_at.isoformat() if tree.staged_at else None
            }
        
        return result

    @staticmethod
    def mark_as_pushed(project_id: int, sample_id: str, sent_id: str = None, tree_user_id: str = None):
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
        
        for tree in query.all():
            tree.status = 'pushed'
            tree.pushed_at = datetime.utcnow()
        
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
