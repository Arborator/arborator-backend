from sqlalchemy import BLOB, Boolean, Column, Integer, String, Boolean, TEXT
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy_utils import ChoiceType

from app import db  # noqa

class Transcription(db.Model):
    __tablename__ = "Klang"
    # id = models.AutoField(primary_key = True)
    # user = models.CharField(max_length = 100)
    # mp3 = models.CharField(max_length = 100)
    # transcription = models.TextField()
    id = Column(Integer, primary_key=True)
    user = Column(String(100), unique=True, nullable=False)
    mp3 = Column(String(100), unique=True, nullable=False)
    transcription = Column(TEXT)
