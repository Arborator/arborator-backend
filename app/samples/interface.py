from typing import List
from mypy_extensions import TypedDict

class SampleInterface(TypedDict, total=False):
    sample_name: str
    sentences: int
    number_trees: int
    tokens: int
    trees_from: List[str]
    tree_by_user: dict[str, int]
    blind_annotation_level: int
