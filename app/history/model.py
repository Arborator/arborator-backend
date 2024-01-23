from sqlalchemy import Column, Boolean, String, Integer, Float
from sqlalchemy_utils import ChoiceType

from app import db
from app.shared.model import BaseM

class History(db.Model, BaseM):
    __tablename__ = "history"
    REQUEST_TYPES = [(1, "search"), (2, "rewrite")]

    id = Column(Integer, primary_key=True)
    user_id = Column(String(256), db.ForeignKey("users.id")) 
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    name = Column(String(256), nullable=False, unique=True)
    request = Column(String, nullable=False)
    type = Column(ChoiceType(REQUEST_TYPES, impl=Integer()))
    favorite = Column(Boolean, default=False)
    date = Column(Float)
    modified_sentences = Column(Integer, nullable=True) # attribute only for rewrite type

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
 

    