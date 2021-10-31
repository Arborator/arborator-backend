from sqlalchemy import BLOB, Boolean, Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy_utils import ChoiceType

from app import db  # noqa

from app.shared.model import BaseM

from .interface import ProjectInterface


class Project(db.Model, BaseM):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    project_name = Column(String(256), nullable=False, unique=True)
    description = Column(String(256))
    image = Column(BLOB)
    # users = db.relationship('User', backref='project_user',lazy='dynamic')
    # texts = db.relationship('Text', backref='project_text',lazy='dynamic')
    # is_private = Column(Boolean, default=False)
    visibility = Column(Integer)
    show_all_trees = Column(Boolean, default=True)
    exercise_mode = Column(Boolean, default=False)
    diff_mode = Column(Boolean, default=False)
    diff_user_id = Column(String(256), nullable=True)

    # default_user_trees = db.relationship('DefaultUserTrees')

    def update(self, changes: ProjectInterface):
        for key, val in changes.items():
            setattr(self, key, val)
        return self

    def __repr__(self):
        return "<project: {}>".format(self.project_name)


class ProjectFeature(db.Model):
    __tablename__ = "feature"
    id = Column(Integer, primary_key=True)
    value = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))


class ProjectMetaFeature(db.Model):
    __tablename__ = "metafeature"
    id = Column(Integer, primary_key=True)
    value = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))


class ProjectAccess(db.Model):
    __tablename__ = "projectaccess"
    ACCESS = [(1, "guest"), (2, "admin")]
    LABEL_TO_LEVEL = {v: k for k, v in dict(ACCESS).items()}
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    user_id = Column(String(256), db.ForeignKey("users.id"))
    access_level = Column(ChoiceType(ACCESS, impl=Integer()))

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self

    def __repr__(self):
        return "<projectAccess,project={},user={},access={} >".format(
            self.project_id, self.user_id, self.access_level
        )


class Access(db.Model):
    """
        userid projectid writeaccess datetime
        userid : contient une ref de l'id du tableau user
        projectid : contient une de ref l'id du tableau projet
        writeaccess contient une boolean (0 only read access, 1 write access)
    """
    __tablename__ = "access"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(256), db.ForeignKey("users.id"))
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    writeaccess = Column(Boolean)
    # Those two columns should be used to detect unused projects : time_created will become the starting point from the migration date
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())


class DefaultUserTrees(db.Model, BaseM):
    __tablename__ = "defaultusertrees"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project")
    user_id = Column(String(256), db.ForeignKey("users.id"))
    username = Column(String(256), nullable=False)
    robot = Column(Boolean, default=False)


# class DefaultUserDiffTree(db.Model, BaseM):
#     __tablename__ = "defaultuserdifftree"
#     id = Column(Integer, primary_key=True)
#     project_id = Column(Integer, db.ForeignKey("projects.id"))
#     project = db.relationship("Project")
#     user_id = Column(String(256), db.ForeignKey("users.id"))


class Robot(db.Model, BaseM):
    __tablename__ = "robots"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project")
    username = Column(String(256), nullable=False)
