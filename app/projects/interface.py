from typing import List
from mypy_extensions import TypedDict


class ProjectInterface(TypedDict, total=False):
    id: int
    project_name: str
    description: str
    image: str
    visibility: int
    blind_annotation_mode: bool
    freezed: bool
    config: str
    language: str
    sync_github: str
    owner: str
    contact_owner: str
    diff_user_id: str
    diff_mode: bool
    collaborative_mode: bool


class ProjectExtendedInterface(ProjectInterface, total=False):
    users: List[str]
    owner_avatar_url: str
    admins: List[str]
    validators: List[str]
    annotators: List[str]
    guests: List[str]
    number_sentences: int 
    number_samples: int
    number_trees: int
    number_tokens: int
    last_access: int
    last_access_write: int

class ProjectShownFeaturesAndMetaInterface(TypedDict, total=False):
    shown_features: List[str]
    shown_meta: List[str]



