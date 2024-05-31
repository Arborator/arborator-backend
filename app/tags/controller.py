

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
        return TagService.add_new_tags(project_name, sample_name, tags, tree) 
    
    def put(self, project_name, sample_name):

        data = request.get_json()
        tag = data.get("tag")
        tree = data.get("tree")
        return TagService.remove_tag(project_name, sample_name, tag, tree)
        

@api.route("/<string:project_name>/tags/<string:username>")
class UserTagsResource(Resource):

    def get(self, project_name, username):

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user = UserService.get_by_username(username)
        if user is not None and UserTagsService.get_by_user_id(user.id):
            return UserTagsService.get_by_user_id(user.id).tags


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

        


        