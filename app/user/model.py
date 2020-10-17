import base64
from datetime import datetime
import json

from flask_login import UserMixin
from sqlalchemy import Integer, Column, String
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
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
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


# TODO : to refactor
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class User(UserMixin, db.Model , BaseM):

    __tablename__ = 'users'

    id = db.Column(db.String(256), primary_key=True)
    auth_provider = db.Column(db.String(256))
    username = db.Column(db.String(60), index=True, unique=True)
    first_name = db.Column(db.String(60), index=True)
    family_name = db.Column(db.String(60), index=True)
    picture_url = db.Column(db.String(128), index=True)
    super_admin = db.Column(db.Boolean, default=False)
    #role = db.Column(db.Integer)
    #project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    #todos = db.relationship('Todo', backref='txt_todos')
    created_date = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)

    def update(self, changes: UserInterface):
        for key, val in changes.items():
            setattr(self, key, val)
        return self



    @staticmethod
    def get_or_create(session, **kwargs):
        instance = session.query(User).filter_by(
            username=kwargs['username']).first()
        if instance:
            instance.last_seen = datetime.utcnow()
            session.commit()
            return instance, False
        else:
            instance = User(**kwargs)
            session.add(instance)
            session.commit()
            return instance, True

    @staticmethod
    def setPictureUrl(session, username, pictureUrl):
        '''
        Modify the user url. Need the session and the username to find it. 
        This method is static void.
        Note: should be interfaced by a service.
        '''
        instance = session.query(User).filter_by(username=username).first()
        if instance:
            instance.picture_url = pictureUrl
            session.commit()

    # def allowed(self, level):
        # return self.access >= level

    def __repr__(self):
        return '<user: {}>'.format(self.username)
