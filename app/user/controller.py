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
from .service import UserService, EmailService

api = Namespace("User", description="Single namespace, single entity")  # noqa



@api.route("/")
class UsersResource(Resource):
    
    @responds(schema=UserSchema(many=True), api=api)
    def get(self) -> List[User]:
        """Get the list of users in the app

        Returns:
            List[User]: the list of the users in the app
        """
        return UserService.get_all()


@api.route("/me")
class UserResource(Resource):

    @responds(schema=UserSchema, api=api)
    def get(self) -> User:
        """Get user information after log in and update last_seen value

        Returns:
            User: User entity
        """
        user = UserService.get_by_id(current_user.id)
        changes: UserInterface = {"last_seen": datetime.utcnow()}
        user = UserService.update(user, changes)
        return user
    
    @responds(schema=UserSchema, api=api)
    @accepts(schema=UserSchema, api=api)
    def put(self): 
        """Update information of user

        Returns:
            User: return user entity with the updated values
        """
        user = UserService.get_by_id(current_user.id)
        changes: UserInterface = request.parsed_obj
        return UserService.update(user,changes)
    
@api.route("/logout")
class UserLogoutResource(Resource):
    
    def get(self):
        """Logout user 

        Returns:
            Response: flask response
        """
        logout_user()
        js = json.dumps({"logout": True}, default=str)
        return Response(js, status=200, mimetype="application/json")

@api.route("/send-email")
class SendEmailResource(Resource):

    def post(self):
        """Send email to user when they are added to a new project"""
        data = request.get_json()
        username = data.get("username")
        role = data.get("role")
        project_name = data.get("projectName")

        EmailService.send_email_to_user(username, role, project_name)