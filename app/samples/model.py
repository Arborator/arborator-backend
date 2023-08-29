from sqlalchemy import Column, Integer, String
from sqlalchemy_utils import ChoiceType

from app import db  # noqa

class SampleBlindAnnotationLevel(db.Model):
    __tablename__ = "blindannotationlevel"
    BLIND_ANNOTATION_LEVEL = [
        (1, "validated_visible"),
        (2, "graphical_feedback"),
        (3, "numerical_feedback"),
        (4, "no_feedback"),
    ]
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    blind_annotation_level = Column(ChoiceType(BLIND_ANNOTATION_LEVEL, impl=Integer()))

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
