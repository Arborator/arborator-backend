from typing import Any, List
from mypy_extensions import TypedDict


class ProjectInterface(TypedDict, total=False):
    id: int
    project_name: str
    description: str
    image: Any
    visibility: int
    show_all_trees: bool
    exercise_mode: bool
    freezed: bool


class ProjectExtendedInterface(ProjectInterface, total=False):
    admins: List[str]
    validators: List[str]
    annotators: List[str]
    guests: List[str]
    number_sentences: int
    number_samples: int
    number_trees: int
    number_tokens: int

class ProjectShownFeaturesAndMetaInterface(TypedDict, total=False):
    shown_features: List[str]
    shown_meta: List[str]



