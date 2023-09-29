from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app import db  
from app.shared.model import BaseM

class UserTags(db.Model, BaseM):
    __tablename__ = 'user_tags'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(256), db.ForeignKey("users.id")) 
    tags = Column(JSONB, nullable=False)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self


    