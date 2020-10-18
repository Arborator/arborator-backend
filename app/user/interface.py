from mypy_extensions import TypedDict
from datetime import datetime


class UserInterface(TypedDict, total=False):
    id: str
    auth_provider: str
    username: str
    first_name: str
    family_name: str
    picture_url: str
    super_admin: bool
    created_date: datetime
    last_seen: datetime
