from datetime import datetime

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
    # default_user_trees: str # TODO : What's the type ?


class ProjectExtendedInterface(ProjectInterface, total=False):
    admins: List[str]
    guests: List[str]
    number_sentences: int
    number_samples: int
    number_trees: int
    number_tokens: int




