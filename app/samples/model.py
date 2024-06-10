from sqlalchemy import Column, Integer, String

from app import db  # noqa

class SampleBlindAnnotationLevel(db.Model):
    __tablename__ = "blindannotationlevel"
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    blind_annotation_level = Column(Integer)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
