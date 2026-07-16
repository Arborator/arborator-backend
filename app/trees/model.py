from datetime import datetime
from app import db


class StagedTree(db.Model):
    """
    Model for tracking trees staged for GitHub push.
    
    """
    __tablename__ = 'staged_trees'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False)
    sample_id = db.Column(db.String(255), nullable=False)
    sent_id = db.Column(db.String(255), nullable=False)
    
    # who owns the tree
    tree_user_id = db.Column(db.String(255), nullable=False)
    
    # admin who marked it for push
    staging_user_id = db.Column(db.String(255), nullable=False)
    
    # Staging dats
    staged_at = db.Column(db.DateTime, nullable=False, default=datetime)
    pushed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='staged')  # 'staged', 'pushed', 'unstaged'
    
    # only one staging per sample
    __table_args__ = (
        db.UniqueConstraint('project_id', 'sample_id', 'sent_id', 'tree_user_id',
                           name='uq_staged_tree'),
    )
    
    def __repr__(self):
        return f'<StagedTree {self.project_id}:{self.sample_id}:{self.sent_id}:{self.tree_user_id}>'


class PinnedTree(db.Model):
    __tablename__ = 'pinned_trees'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False)
    sample_id = db.Column(db.String(255), nullable=False)
    sent_id = db.Column(db.String(255), nullable=False)
    tree_user_id = db.Column(db.String(255), nullable=False)
    
    # Who pinned this tree
    pinned_by = db.Column(db.String(255), nullable=False)
    pinned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('project_id', 'sample_id', 'sent_id', 'tree_user_id', 'pinned_by',
                           name='uq_pinned_tree'),
    )
    
    def __repr__(self):
        return f'<PinnedTree {self.project_id}:{self.sample_id}:{self.sent_id}:{self.tree_user_id}>'
