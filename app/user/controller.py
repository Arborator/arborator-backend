from datetime import datetime
from typing import List

from flask import session
from flask_accepts.decorators.decorators import responds
from flask_restx import Namespace, Resource

from .interface import UserInterface
from .model import User
from .schema import UserSchema
from .service import UserService

api = Namespace("User", description="Single namespace, single entity")  # noqa



@api.route("/")
class UsersResource(Resource):
    "Users"
    @responds(schema=UserSchema(many=True), api=api)
    def get(self) -> List[User]:
        return UserService.get_all()


@api.route("/me")
class UserResource(Resource):
    "User"

    @responds(schema=UserSchema, api=api)
    def get(self) -> User:
        user_id = session.get("user_id")
        if not user_id:
            user_id = session.get("_user_id")

        user = UserService.get_by_id(user_id)
        changes: UserInterface = {"last_seen": datetime.utcnow()}
        user = UserService.update(user, changes)
        return user
