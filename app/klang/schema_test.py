from pytest import fixture

from .model import Transcription
from .schema import TranscriptionSchema
from .interface import TranscriptionInterface


@fixture
def schema() -> TranscriptionSchema:
    return TranscriptionSchema()


def test_TranscriptionSchema_create(schema: TranscriptionSchema):
    assert schema


def test_TranscriptionSchema_works(schema: TranscriptionSchema):
    params: TranscriptionInterface = schema.load(
        {
            "user": "test",
            "mp3": "test",
            "sound": "test",
            "story": "test",
            "accent": "test",
            "monodia": "test",
            "title": "test",
            "transcription": [["test"]],
        }
    )
    user = Transcription(**params)

    assert user.user == "test"
    assert user.mp3 == "test"
    assert user.sound == "test"
    assert user.story == "test"
    assert user.accent == "test"
    assert user.monodia == "test"
    assert user.title == "test"
    assert user.transcription == [["test"]]
