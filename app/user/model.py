import base64
from datetime import datetime
import json

from flask_login import UserMixin
from sqlalchemy import Integer, Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import DeclarativeMeta

from app import db, login_manager  # noqa

from .interface import UserInterface


class BaseM(object):
    def as_json(self, exclude=[], include={}):
        json_rep = dict()
        for k in vars(self):
            # print(getattr(self, k))
            if k in exclude:
                # print(k)
                continue
            elif k[0] == "_":
                continue
            elif type(getattr(self, k)) is bytes:
                # print('yay')
                # print(getattr(self, k))
                json_rep[k] = str(base64.b64encode(getattr(self, k)))
                # json_rep[k] = str(getattr(self, k))
            else:
                json_rep[k] = getattr(self, k)
        for k in include:
            json_rep[k] = include[k]
        return json_rep


class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [
                x for x in dir(obj) if not x.startswith("_") and x != "metadata"
            ]:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


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
