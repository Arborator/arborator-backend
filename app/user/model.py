from flask_login import UserMixin
from sqlalchemy import Column, String, Boolean, DateTime

from app import db  # noqa

from app.shared.model import BaseM

from .interface import UserInterface


class User(UserMixin, db.Model, BaseM):

    __tablename__ = "users"

    id = Column(String(256), primary_key=True)
    auth_provider = Column(String(256))
    username = Column(String(60), index=True, unique=True)
    first_name = Column(String(60), index=True)
    family_name = Column(String(60), index=True)
    picture_url = Column(String(128), index=True)
    super_admin = Column(Boolean, default=False)
    # role = Column(Integer)
    # project_id = Column(Integer, db.ForeignKey('projects.id'))
    # todos = db.relationship('Todo', backref='txt_todos')
    created_date = Column(DateTime)
    last_seen = Column(DateTime)

    def update(self, changes: UserInterface):
        for key, val in changes.items():
            setattr(self, key, val)
        return self

    def __repr__(self):
        return "<user: {}>".format(self.username)
