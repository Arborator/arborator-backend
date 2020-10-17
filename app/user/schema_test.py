from datetime import datetime

from pytest import fixture

from .model import User
from .schema import UserSchema
from .interface import UserInterface


@fixture
def schema() -> UserSchema:
    return UserSchema()


def test_UserSchema_create(schema: UserSchema):
    assert schema


def test_UserSchema_works(schema: UserSchema):
    params: UserInterface = schema.load(
        {
            "id": "1",
            "auth_provider": "google",
            "username": "JohnDoe",
            "first_name": "John",
            "family_name": "Doe",
            "picture_url": "www.google.com",
            "super_admin": True,
            "created_date": str(datetime.now()),
            "last_seen": str(datetime.now()),
        }
    )
    user = User(**params)

    assert user.id == "1"
    assert user.auth_provider == "google"
    assert user.username == "JohnDoe"
    assert user.first_name == "John"
    assert user.family_name == "Doe"
    assert user.picture_url == "www.google.com"
    assert user.super_admin == True
