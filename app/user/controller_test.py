from datetime import datetime

from unittest.mock import patch
from flask.testing import FlaskClient

from app.test.fixtures import client, app  # noqa
from .service import UserService
from .schema import UserSchema
from .model import User
from .interface import UserInterface
from . import BASE_ROUTE


def make_user(
    id: str = "123",
    auth_provider: str = "google",
    username: str = "JohnDoe",
    first_name: str = "John",
    family_name: str = "Doe",
    email: str = "JohnDoe@gmail.com",
    not_share_email: bool = False,
    receive_newsletter: bool = True,
    picture_url: str = "www.google.com",
    super_admin: bool = False,
    created_date: datetime = datetime.utcnow(),
    last_seen: datetime = datetime.utcnow(),
) -> User:
    return User(
        id=id,
        auth_provider=auth_provider,
        username=username,
        first_name=first_name,
        family_name=family_name,
        email=email,
        not_share_email=not_share_email,
        receive_newsletter=receive_newsletter,
        picture_url=picture_url,
        super_admin=super_admin,
        created_date=created_date,
        last_seen=last_seen,
    )


class TestUserResource:
    @patch.object(
        UserService,
        "get_all",
        lambda: [
            make_user("123", username="user1"),
            make_user("456", username="user2"),
        ],
    )
    def test_get(self, client: FlaskClient):  # noqa
        with client:
            results = client.get(f"/api/{BASE_ROUTE}", follow_redirects=True).get_json()
            expected = (
                UserSchema(many=True)
                .dump(
                    [
                    make_user("123", username="user1"),
                    make_user("456", username="user2"),
                    ]
                )
                
            )
            for r in results:
                assert r in expected

