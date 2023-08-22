import json

from flask import request
from flask_restx import Namespace, Resource

from app.user.service import UserService
from app.projects.service import ProjectService
from .service import TagService, UserTagsService

api = Namespace(
    "Tags",
    description="Endpoints for dealing with tags",
)  # noqa

@api.route("/<string:project_name>/samples/<string:sample_name>/tags")
class TagsResource(Resource):

    def post(self, project_name, sample_name):

        data = request.get_json()
        tags = data.get("tags")
        tree = data.get("tree")
        TagService.add_new_tags(project_name, sample_name, tags, tree)
        return {'status': 'ok'}
    
    

@api.route("/<string:project_name>/tags/<string:username>")
class UserTagsResource(Resource):

    def get(self, project_name, username):

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        if UserTagsService.get_by_user_id(user_id):
            return UserTagsService.get_by_user_id(user_id).tags


    def post(self, project_name, username):

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        data = request.get_json()
        tags = data.get("tags")
        user_id = UserService.get_by_username(username).id
        user_tags = {
            "user_id": user_id,
            "tags": [tags]
        }
        UserTagsService.create_or_update(user_tags)

        


        