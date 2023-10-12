from sqlalchemy import Column, Text, ForeignKey, Integer, JSON, String


from app import db  # noqa

from app.shared.model import BaseM

class Constructicon(db.Model, BaseM):
    __tablename__ = 'constructicon'

    id = Column(String(256), primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    grew_query = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self