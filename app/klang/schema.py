from marshmallow import fields, Schema


class TranscriptionSchema(Schema):
    """Transcription schema"""

    id = fields.String(attribute="id")
    user = fields.String(attribute="user")
    mp3 = fields.String(attribute="mp3")
    sound = fields.String(attribute="sound")
    story = fields.String(attribute="story")
    accent = fields.String(attribute="accent")
    monodia = fields.String(attribute="monodia")
    title = fields.String(attribute="title")
    transcription = fields.String(attribute="transcription")