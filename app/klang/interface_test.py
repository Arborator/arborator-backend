from pytest import fixture
from .model import Transcription
from .interface import TranscriptionInterface


@fixture
def interface() -> TranscriptionInterface:
    return TranscriptionInterface(
        mp3="test",
        sound="test",
        story="test",
        accent="test",
        monodia="test",
        title="test",
        transcription="test",
    )


def test_UserInterface_create(interface: TranscriptionInterface):
    assert interface


# def test_UserInterface_works(interface: TranscriptionInterface):
#     transcription = Transcription(**interface)
#     assert transcription
