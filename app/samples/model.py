from sqlalchemy import Column, Integer, String

from app import db  # noqa

class SampleBlindAnnotationLevel(db.Model):
    """ This class represents the level of blind annotation 
        blind annotation levels are 
            1: validated_visible
            2: local_feedback
            3: global_feedback
            4: no_feedback
            
    """
    __tablename__ = "blindannotationlevel"
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(256), nullable=False)
    project_id = Column(Integer, db.ForeignKey("projects.id"))
    blind_annotation_level = Column(Integer)

    def update(self, changes):
        for key, val in changes.items():
            setattr(self, key, val)
        return self
