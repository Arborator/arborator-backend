from typing import List
from mypy_extensions import TypedDict

class TopUserInterface(TypedDict, total=False):
    username: str
    trees_number: int
    user_avatar: str
    
class LastReadAccessInterface(TypedDict, total=False):
    last_read: int
    last_read_username: str
    
class LastWriteAccessInterface(TypedDict, total=False):
    last_write: int
    last_write_username: str
    
class StatProjectInterface(TypedDict, total=False):
    users: List[str]
    samples_number: int
    trees_number: int
    sentences_number: int
    tokens_number: int
    top_user: TopUserInterface
    last_read: LastReadAccessInterface
    last_write: LastWriteAccessInterface
    

    