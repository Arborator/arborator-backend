from flask import request
from flask_restx import Namespace, Resource

from app.projects.service import ProjectService
from .service import HistoryService

api = Namespace(
    "History",
    description="Endpoints for dealing with grew search and rewrite history"
)


@api.route("/<string:project_name>/history")
class HistoryResource(Resource):

    def get(self, project_name):
        project = ProjectService.get_by_name(project_name)
        return HistoryService.get_all_user_history(project.id)
    
    def post(self, project_name):
        project = ProjectService.get_by_name(project_name)
        data = request.get_json()
        data["project_id"] = project.id
        new_history_record = HistoryService.create(data)
        return new_history_record
    
    def delete(self, project_name):
        project = ProjectService.get_by_name(project_name)
        HistoryService.delete_all_history(project.id)
        return { "status": "ok" }
    

@api.route("/<string:project_name>/history/<string:history_id>")
class HistoryRecordResource(Resource):

    def delete(self, project_name, history_record_id):
        HistoryService.delete_by_id(history_record_id)
        return { "status": "ok" }
    







        

