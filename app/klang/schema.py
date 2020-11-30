from marshmallow import fields, Schema


class TranscriptionSchema(Schema):
    """Transcription schema"""

    user = fields.String(attribute="user")
    mp3 = fields.String(attribute="mp3")
    sound = fields.String(attribute="sound")
    story = fields.String(attribute="story")
    accent = fields.String(attribute="accent")
    monodia = fields.String(attribute="monodia")
    title = fields.String(attribute="title")
    transcription = fields.List(fields.List(fields.String), attribute="transcription")