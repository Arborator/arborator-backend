from datetime import datetime
from typing import List

from app.test.fixtures import app, db  # noqa
from flask_sqlalchemy import SQLAlchemy

from .interface import UserInterface
from .model import User
from .service import UserService  # noqa


def test_get_all(db: SQLAlchemy):  # noqa
    yin: User = User(
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
    yang: User = User(
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
    db.session.add(yin)
    db.session.add(yang)
    db.session.commit()

    results: List[User] = UserService.get_all()

    assert len(results) == 2
    assert yin in results and yang in results


def test_update(db: SQLAlchemy):  # noqa
    yin: User = User(
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

    db.session.add(yin)
    db.session.commit()
    updates: UserInterface = dict(first_name="New first_name")

    UserService.update(yin, updates)

    result: User = User.query.get(yin.id)
    assert result.first_name == "New first_name"


def test_delete_by_id(db: SQLAlchemy):  # noqa
    yin: User = User(
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
    yang: User = User(
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
    db.session.add(yin)
    db.session.add(yang)
    db.session.commit()

    UserService.delete_by_id("1")
    db.session.commit()

    results: List[User] = User.query.all()

    assert len(results) == 1
    assert yin not in results and yang in results


def test_create(db: SQLAlchemy):  # noqa

    yin: UserInterface = dict(
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
    UserService.create(yin)
    results: List[User] = User.query.all()

    assert len(results) == 1

    for k in yin.keys():
        assert getattr(results[0], k) == yin[k]
