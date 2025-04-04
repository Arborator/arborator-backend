from sqlalchemy import Column, Boolean, String, Integer, Float

from app import db
from app.shared.model import BaseM

class History(db.Model, BaseM):
    """History representation in the db"""
    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True)
    user_id = Column(String(256), db.ForeignKey("users.id")) 
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    request = Column(String, nullable=False)
    type = Column(String, nullable=False)
    favorite = Column(Boolean, default=False)
    date = Column(Float)
    modified_sentences = Column(Integer, nullable=True) # attribute only for rewrite type

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
 

    