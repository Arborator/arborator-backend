from typing import List
from mypy_extensions import TypedDict

class ConstructiconInterfce(TypedDict, total=False):
    id: str
    title: str
    description: str
    grew_query: str
    tags: List[str]
    
    