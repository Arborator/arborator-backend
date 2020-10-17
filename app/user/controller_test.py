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
    # id: str = "123",
    # name: str = "Test user",
    # purpose: str = "Test purpose",
    id: str = "123",
    auth_provider: str = "google",
    username: str = "JohnDoe",
    first_name: str = "John",
    family_name: str = "Doe",
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
        picture_url=picture_url,
        super_admin=super_admin,
        created_date=created_date,
        last_seen=last_seen,
    )


# class TestUserResource:
#     @patch.object(
#         UserService,
#         "get_all",
#         lambda: [
#             make_user(id="123", username="username 1"),
#             make_user(id="456", username="username 2"),
#         ],
#     )
#     def test_get(self, client: FlaskClient):  # noqa
#         with client:
#             results = client.get(f"/api/{BASE_ROUTE}", follow_redirects=True).get_json()
#             expected = UserSchema(many=True).dump(
#                 [
#                     make_user(id="123", username="username 1"),
#                     make_user(id="456", username="username 2"),
#                 ]
#             )
#             for r in results:
#                 assert r in expected

#     @patch.object(UserService, "create", lambda create_request: User(**create_request))
#     def test_post(self, client: FlaskClient):  # noqa
#         with client:

#             payload = dict(id="123", username="username 1")
#             result = client.post(f"/api/{BASE_ROUTE}/", json=payload).get_json()
#             expected = UserSchema().dump(
#                 User(name=payload["name"], purpose=payload["purpose"])
#             )
#             assert result == expected


# def fake_update(user: User, changes: UserInterface) -> User:
#     # To fake an update, just return a new object
#     updated_User = User(id=user.id, username=changes["username"])
#     return updated_User






# class TestUserIdResource:
#     @patch.object(UserService, "get_by_id", lambda id: make_user(id=id))
#     def test_get(self, client: FlaskClient):  # noqa
#         with client:
#             result = client.get(f"/api/{BASE_ROUTE}/123").get_json()
#             expected = make_user(id=123)
#             print(f"result = ", result)
#             assert result["userId"] == expected.id

#     @patch.object(UserService, "delete_by_id", lambda id: id)
#     def test_delete(self, client: FlaskClient):  # noqa
#         with client:
#             result = client.delete(f"/api/{BASE_ROUTE}/123").get_json()
#             expected = dict(status="Success", id=123)
#             assert result == expected

#     @patch.object(UserService, "get_by_id", lambda id: make_user(id=id))
#     @patch.object(UserService, "update", fake_update)
#     def test_put(self, client: FlaskClient):  # noqa
#         with client:
#             result = client.put(
#                 f"/api/{BASE_ROUTE}/123",
#                 json={"name": "New User", "purpose": "New purpose"},
#             ).get_json()
#             expected = UserSchema().dump(
#                 User(id=123, name="New User", purpose="New purpose")
#             )
#             assert result == expected
