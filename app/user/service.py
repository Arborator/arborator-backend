from app import db
from typing import List
from .model import User
from .interface import UserInterface


class UserService:
    @staticmethod
    def get_all() -> List[User]:
        return User.query.all()

    @staticmethod
    def get_by_id(id: int) -> User:
        return User.query.get(id)

    @staticmethod
    def update(user: User, User_change_updates: UserInterface) -> User:
        user.update(User_change_updates)
        db.session.commit()
        return user

    @staticmethod
    def delete_by_id(id: int) -> List[int]:
        user = User.query.filter(User.id == id).first()
        if not user:
            return []
        db.session.delete(user)
        db.session.commit()
        return [id]


    ## The creation is handled in the oath blueprint
    ## TODO : do the creation here
    # @staticmethod
    # def create(new_attrs: WidgetInterface) -> Widget:
    #     new_widget = Widget(name=new_attrs["name"], purpose=new_attrs["purpose"])

    #     db.session.add(new_widget)
    #     db.session.commit()

    #     return new_widget
