from sqlalchemy import Column, Integer, String, TEXT

from app import db  # noqa

class Transcription():
    def __init__(self, user, mp3, sound, story, accent, monodia, title, transcription) -> None:
        self.user = user
        self.mp3 = mp3
        self.sound = sound
        self.story = story
        self.accent = accent
        self.monodia = monodia
        self.title = title
        self.transcription = transcription
