from datetime import datetime
from typing import List

from app.test.fixtures import app, db  # noqa
from flask_sqlalchemy import SQLAlchemy

from .interface import UserInterface
from .model import User
from .service import UserService  # noqa


def test_get_all(db: SQLAlchemy):  # noqa
    user1: User = User(
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
    user2: User = User(
        id="2",
        auth_provider="github",
        username="JamesCarl",
        first_name="James",
        family_name="Carl",
        picture_url="www.google.com",
        super_admin=True,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    results: List[User] = UserService.get_all()

    assert len(results) == 2
    assert user1 in results and user2 in results


def test_get_by_username(db: SQLAlchemy):  # noqa
    user1: User = User(
        id="1",
        auth_provider="google",
        username="user1",
        first_name="John",
        family_name="Doe",
        picture_url="www.google.com",
        super_admin=True,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    user2: User = User(
        id="2",
        auth_provider="github",
        username="user2",
        first_name="James",
        family_name="Carl",
        picture_url="www.google.com",
        super_admin=True,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    retrieved_user1 = UserService.get_by_username("user1")
    retrieved_user2 = UserService.get_by_username("user2")

    assert retrieved_user1.username == "user1"
    assert retrieved_user1.id == "1"

    assert retrieved_user2.username == "user2"
    assert retrieved_user2.id == "2"


def test_update(db: SQLAlchemy):  # noqa
    user1: User = User(
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

    db.session.add(user1)
    db.session.commit()
    updates: UserInterface = dict(first_name="New first_name")

    UserService.update(user1, updates)

    result: User = User.query.get(user1.id)
    assert result.first_name == "New first_name"


def test_delete_by_id(db: SQLAlchemy):  # noqa
    user1: User = User(
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
    user2: User = User(
        id="2",
        auth_provider="github",
        username="JamesCarl",
        first_name="James",
        family_name="Carl",
        picture_url="www.google.com",
        super_admin=True,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    UserService.delete_by_id("1")
    db.session.commit()

    results: List[User] = User.query.all()

    assert len(results) == 1
    assert user1 not in results and user2 in results


def test_create(db: SQLAlchemy):  # noqa
    user1: UserInterface = dict(
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
    UserService.create(user1)
    results: List[User] = User.query.all()

    assert len(results) == 1

    for k in user1.keys():
        assert getattr(results[0], k) == user1[k]


def test_change_super_admin(db: SQLAlchemy):
    user1: User = User(
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
    user2: User = User(
        id="2",
        auth_provider="github",
        username="JamesCarl",
        first_name="James",
        family_name="Carl",
        picture_url="www.google.com",
        super_admin=False,
        created_date=datetime.utcnow(),
        last_seen=datetime.utcnow(),
    )

    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    UserService.change_super_admin(user1, False)
    UserService.change_super_admin(user2, True)

    changed_user1 = UserService.get_by_id("1")
    changed_user2 = UserService.get_by_id("2")

    assert changed_user1.super_admin == False
    assert changed_user2.super_admin == True
