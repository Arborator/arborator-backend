from app import db
from typing import List
from .model import User
from .interface import UserInterface
from flask_login import login_user

from app import login_manager


class UserService:
    @staticmethod
    def get_all() -> List[User]:
        return User.query.all()

    @staticmethod
    def get_by_id(id: str) -> User:
        return User.query.get(id)

    @login_manager.user_loader
    @staticmethod
    def login_by_id(id: str) -> User:
        return User.query.get(id)

    @staticmethod
    def update(user: User, User_change_updates: UserInterface) -> User:
        user.update(User_change_updates)
        db.session.commit()
        return user

    @staticmethod
    def delete_by_id(id: str) -> List[str]:
        user = User.query.filter(User.id == id).first()
        if not user:
            return []
        db.session.delete(user)
        db.session.commit()
        return [id]

    @staticmethod
    def make_valid_nickname(nickname):
        # return re.sub('[^a-zA-Z0-9_\.]', '', nickname)
        return nickname.replace(" ", "")

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(username=nickname).first() is None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=new_nickname).first() is None:
                break
            version += 1
        return new_nickname

    ## The creation is handled in the oath blueprint
    ## TODO : do the creation here
    @staticmethod
    def create(new_attrs: UserInterface) -> User:
        new_user = User(**new_attrs)

        db.session.add(new_user)
        db.session.commit()

        return new_user
