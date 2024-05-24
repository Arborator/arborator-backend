from flask import request
from flask_restx import Namespace, Resource
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user

from app.projects.service import ProjectService
from .service import HistoryService
from .schema import GrewHistorySchema
from .interface import GrewHistoryInterface

api = Namespace(
    "History",
    description="Endpoints for dealing with grew search and rewrite history"
)


@api.route("/<string:project_name>/history")
class HistoryResource(Resource):

    @responds(schema=GrewHistorySchema(many=True), api=api)
    def get(self, project_name):
        project = ProjectService.get_by_name(project_name)
        return HistoryService.get_all_user_history(project.id)
    
    @accepts(schema=GrewHistorySchema, api=api)
    @responds(schema=GrewHistorySchema, api=api)
    def post(self, project_name):
        project = ProjectService.get_by_name(project_name)
        data: GrewHistoryInterface = request.parsed_obj
        data["project_id"] = project.id
        data["user_id"] = current_user.id
        new_history_record = HistoryService.create(data)
        return new_history_record
    
    def delete(self, project_name):
        project = ProjectService.get_by_name(project_name)
        HistoryService.delete_all_history(project.id)
        return { "status": "ok" }
    

@api.route("/<string:project_name>/history/<string:history_uuid>")
class HistoryRecordResource(Resource):

    @responds(schema=GrewHistorySchema, api=api)
    def put(self, project_name, history_uuid):
        changes: GrewHistoryInterface = request.get_json()
        project = ProjectService.get_by_name(project_name)
        history_record = HistoryService.get_by_uuid(project.id, history_uuid)
        updated_record = HistoryService.update(history_record, changes)
        return updated_record

    def delete(self, project_name, history_uuid):
        project = ProjectService.get_by_name(project_name)
        history_record = HistoryService.get_by_uuid(project.id, history_uuid)
        HistoryService.delete_by_id(history_record.id)
        return { "status": "ok" }

    