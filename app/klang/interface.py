from mypy_extensions import TypedDict


class TranscriptionInterface(TypedDict, total=False):
    user: str
    mp3: str
    sound: str
    story: str
    accent: str
    monodia: str
    title: str
    transcription: str
