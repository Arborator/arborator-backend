from flask import request
from flask_restx import Namespace, Resource
 
from .service import TagService

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


        