from typing import List
from mypy_extensions import TypedDict

class TopUserInterface(TypedDict, total=False):
    """typed interface for top user info"""
    username: str
    trees_number: int
    user_avatar: str
    
class LastReadAccessInterface(TypedDict, total=False):
    """typed interface for last read access"""
    last_read: int
    last_read_username: str
    
class LastWriteAccessInterface(TypedDict, total=False):
    """typed interface for last write access"""
    last_write: int
    last_write_username: str
    
class StatProjectInterface(TypedDict, total=False):
    """typed interface for project statistics"""
    users: List[str]
    samples_number: int
    trees_number: int
    sentences_number: int
    tokens_number: int
    top_user: TopUserInterface
    last_read: LastReadAccessInterface
    last_write: LastWriteAccessInterface
    

    