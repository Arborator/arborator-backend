from datetime import datetime

from pytest import fixture
from .model import User
from .interface import UserInterface


@fixture
def interface() -> UserInterface:
    return UserInterface(
        id="1",
        auth_provider="google",
        username="JohnDoe",
        first_name="John",
        family_name="Doe",
        picture_url="www.google.com",
        super_admin=True,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )


def test_UserInterface_create(interface: UserInterface):
    assert interface


def test_UserInterface_works(interface: UserInterface):
    user = User(**interface)
    assert user
