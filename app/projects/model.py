from sqlalchemy import Boolean, Column, Integer, String, Boolean, Float

from app import db  # noqa

from app.shared.model import BaseM
from app.github.model import GithubRepository, GithubCommitStatus
from app.history.model import History
from app.constructicon.model import Constructicon

from .interface import ProjectInterface


class Project(db.Model, BaseM):
    """Project entity"""
    
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    project_name = Column(String(256), nullable=False, unique=True)
    description = Column(String(256))
    image = Column(String(256), nullable=True)
    visibility = Column(Integer)
    blind_annotation_mode = Column(Boolean, default=False)
    diff_mode = Column(Boolean, default=False)
    diff_user_id = Column(String(256), nullable=True)
    freezed = Column(Boolean, default=False)
    config = Column(String(256), nullable=True)
    language = Column(String(256), nullable=True)
    collaborative_mode = Column(Boolean, default=True)

    feature = db.relationship("ProjectFeature", cascade="all,delete", backref="projects")
    meta_feature = db.relationship("ProjectMetaFeature", cascade="all,delete", backref="projects")
    project_access = db.relationship("ProjectAccess", cascade="all,delete", backref="projects")
    project_last_access = db.relationship("LastAccess", cascade="all,delete", backref="projects")
    github_repository = db.relationship(GithubRepository, cascade="all,delete", backref="projects", uselist=False)
    github_commit_status = db.relationship(GithubCommitStatus, cascade="all,delete", backref="projects")
    constructicon = db.relationship(Constructicon, cascade="all, delete", backref="projects")
    history = db.relationship(History, cascade="all, delete", backref="projects")

    def update(self, changes: ProjectInterface):
        for key, val in changes.items():
            setattr(self, key, val)
        return self

    def __repr__(self):
        return "<project: {}>".format(self.project_name)


class ProjectFeature(db.Model):
    """Feature entity represents the feature that is visible in the tree view"""
    
    __tablename__ = "feature"
    id = Column(Integer, primary_key=True)
    value = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id", ondelete="CASCADE"))


class ProjectMetaFeature(db.Model):
    """Meta feature entity represents the feature that is also visible in the tree view"""
    
    __tablename__ = "metafeature"
    id = Column(Integer, primary_key=True)
    value = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id", ondelete="CASCADE"))


class ProjectAccess(db.Model):
    """Different type of user access in the project"""
    
    __tablename__ = "projectaccess"
    ACCESS = [(1, "annotator"), (2, "validator"), (3, "admin"), (4, "guest")]
    LABEL_TO_LEVEL = {v: k for k, v in dict(ACCESS).items()}
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(String(256), db.ForeignKey("users.id"))
    access_level = Column(Integer, nullable=False)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self


class LastAccess(db.Model):
    """Last user access entity that contains the last read and the last write"""
    
    __tablename__ = "last_access"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(256), db.ForeignKey("users.id")) # unique
    project_id = Column(Integer, db.ForeignKey("projects.id", ondelete="CASCADE")) # unique
    last_read = Column(Float, nullable=True )
    last_write = Column(Float, nullable=True)

