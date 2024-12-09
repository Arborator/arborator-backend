from mypy_extensions import TypedDict
from datetime import datetime


class UserInterface(TypedDict, total=False):
    """Typed interface to deal with user entity"""
    id: str
    auth_provider: str
    github_access_token: str
    username: str
    first_name: str
    family_name: str
    email: str
    not_share_email: bool
    receive_newsletter: bool
    picture_url: str
    super_admin: bool
    created_date: datetime
    last_seen: datetime
