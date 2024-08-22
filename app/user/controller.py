from datetime import datetime
import json
from typing import List

from flask import request, Response
from flask_login import current_user, logout_user
from flask_accepts.decorators.decorators import responds, accepts
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
        user = UserService.get_by_id(current_user.id)
        changes: UserInterface = {"last_seen": datetime.utcnow()}
        user = UserService.update(user, changes)
        return user
    
    @responds(schema=UserSchema, api=api)
    @accepts(schema=UserSchema, api=api)
    def put(self): 
        user = UserService.get_by_id(current_user.id)
        changes: UserInterface = request.parsed_obj
        return UserService.update(user,changes)
    
@api.route("/logout")
class UserLogoutResource(Resource):
    
    def get(self):
        logout_user()
        js = json.dumps({"logout": True}, default=str)
        return Response(js, status=200, mimetype="application/json")
