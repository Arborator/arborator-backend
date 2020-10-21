from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy_utils import ChoiceType

from app import db  # noqa


class SampleRole(db.Model):
    __tablename__ = "samplerole"
    ROLES = [(1, "annotator"), (2, "validator")]
    LABEL_TO_ROLES = {v: k for k, v in dict(ROLES).items()}

    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    user_id = Column(String(256), db.ForeignKey("users.id"))
    role = Column(ChoiceType(ROLES, impl=Integer()))
    # __table_args__ = (UniqueConstraint('sample_name', 'project_id', name='_sample_name_project_id_uc'),)


class SampleExerciseLevel(db.Model):
    __tablename__ = "exerciselevel"
    EXERCISE_LEVEL = [
        (1, "teacher_visible"),
        (2, "graphical_feedback"),
        (3, "numerical_feedback"),
        (4, "no_feedback"),
    ]
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    exercise_level = Column(ChoiceType(EXERCISE_LEVEL, impl=Integer()))

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
