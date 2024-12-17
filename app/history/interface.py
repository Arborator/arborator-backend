from mypy_extensions import TypedDict

class GrewHistoryInterface(TypedDict, total=False):
    """Typed interface for grew history"""
    id: int
    uuid: str
    request: str
    type: str
    favorite: bool
    date: int
    modified_sentences: int
    