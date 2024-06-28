import json

from flask import request
from flask_accepts.decorators.decorators import accepts, responds
from flask_restx import Namespace, Resource

from .interface import ConstructiconInterfce
from .schema import ConstructiconSchema
from .service import ConstructiconService
from ..projects.service import ProjectService, ProjectAccessService

api = Namespace(
    "Constructicon",
    description="Endpoints for dealing with constructicon, cross-linguistical and treebank-wise",
)  # noqa


@api.route("/project/<string:project_name>")
class ConstructiconForProjectResource(Resource):
    """Views for dealing for constructicon for a project"""

    @responds(schema=ConstructiconSchema(many=True), api=api)
    def get(self, project_name: str):
        """Get the list of constructicon for a project"""
        project = ProjectService.get_by_name(project_name)
        return ConstructiconService.get_all_by_project_id(project.id)

    @accepts(schema=ConstructiconSchema, api=api)
    @responds(schema=ConstructiconSchema, api=api)
    def post(self, project_name: str):
        """Create a constructicon for a project"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        if not project:
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        data: ConstructiconInterfce = request.parsed_obj
        data["project_id"] = project.id
        new_or_updated_constructicon_entry = ConstructiconService.create_or_update(data)
        return new_or_updated_constructicon_entry

@api.route("/project/<string:project_name>/<string:constructicon_id>")
class ConstructiconEntryForProjectResource(Resource):
    def delete(self, project_name: str, constructicon_id: str):
        """Delete a constructicon for a project"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        if not project:
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        ConstructiconService.delete_by_id(constructicon_id)
        return {"status": "success"}


@api.route("/project/<string:project_name>/upload-entire-constructicon")
class ConstructiconUploadForProjectResource(Resource):
    def post(self, project_name: str):
        """Delete a constructicon for a project"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        if not project:
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        fname = list(request.files.keys())[0]
        if ".json" not in fname:
            return {"status": "failure", "error": "FILE IS NOT A .JSON FILE"}

        file = request.files.get(fname)
        filecontent = file.read()

        # Parse the file as JSON
        try:
            data = json.loads(filecontent)
            for entry in data:
                entry["project_id"] = project.id
                ConstructiconService.create_or_update(entry)
        except ValueError as e:
            print(e)
            return {"status": "failure", "error": "Invalid JSON."}
        except Exception as e:
            print(e)
            return {"status": "failure", "error": "Something went wrong."}

        return {"success": True}
