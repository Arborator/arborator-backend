from sqlalchemy import Column, Integer, String
from sqlalchemy_utils import ChoiceType

from app import db  # noqa

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
