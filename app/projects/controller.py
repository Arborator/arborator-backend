import datetime
import json
import os
import re
import base64
from typing import List


from flask import abort, current_app, request, jsonify
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from werkzeug.utils import secure_filename
import werkzeug

from app.utils.grew_utils import GrewService
from .interface import (
    ProjectExtendedInterface,
    ProjectInterface,
    ProjectShownFeaturesAndMetaInterface,
)
from .model import Project, ProjectAccess
from .schema import (
    ProjectExtendedSchema,
    ProjectSchema,
    ProjectSchemaCamel,
    ProjectFeaturesAndMetaSchema,
)
from .service import (
    LastAccessService,
    ProjectAccessService,
    ProjectFeatureService,
    ProjectMetaFeatureService,
    ProjectService,
)
from app.user.service import UserService

api = Namespace("Project", description="Endpoints for dealing with projects")  # noqa


@api.route("/")
class ProjectResource(Resource):
    "Project"

    @responds(schema=ProjectExtendedSchema(many=True), api=api)
    def get(self) -> List[ProjectExtendedInterface]:
        """Get all projects"""

        projects_extended_list: List[ProjectExtendedInterface] = []

        projects: List[Project] = Project.query.all()

        grew_projects = GrewService.get_projects()

        grewnames = set([project["name"] for project in grew_projects])
        dbnames = set([project.project_name for project in projects])
        common = grewnames & dbnames

        for project in projects:
            if ProjectAccessService.check_project_access(
                project.visibility, project.id
            ):
                if project.project_name not in common:
                    continue

                (
                    project.admins,
                    project.validators,
                    project.annotators,
                    project.guests,
                ) = ProjectAccessService.get_all(project.id)

                if project.admins:
                    project.owner = project.admins[0]
                    project.contact_owner = UserService.get_by_username(project.admins[0]).email
                else: 
                    project.owner = ''
                    project.contact_owner = ''
                    
                if project.github_repository:
                    project.sync_github = project.github_repository.repository_name
                else:
                    project.sync_github = ''
                
                (
                    last_access,
                    last_write_access,
                ) = LastAccessService.get_project_last_access(
                    project.project_name
                )
                now = datetime.datetime.now().timestamp()
                project.last_access = last_access - now
                project.last_write_access = last_write_access - now

                for grew_project in grew_projects:
                    if grew_project["name"] == project.project_name:
                        project.users = grew_project["users"]
                        project.number_sentences = grew_project["number_sentences"]
                        project.number_samples = grew_project["number_samples"]
                        project.number_tokens = grew_project["number_tokens"]
                        project.number_trees = grew_project["number_trees"]
                projects_extended_list.append(project)

        return projects_extended_list

    @responds(schema=ProjectSchema)
    def post(self) -> Project:
        "Create a single Project"
        try:
            creator_id = current_user.id
        except:
            abort(401, "User not loged in")

        # KK : Make a unified schema for all http request related to project
        # ... and have the schema taking JS camelcase typing
        parser = reqparse.RequestParser()
        parser.add_argument(name="projectName", type=str)
        parser.add_argument(name="description", type=str)
        parser.add_argument(name="blindAnnotationMode", type=bool)
        parser.add_argument(name="visibility", type=int)
        parser.add_argument(name="config", type=str)
        parser.add_argument(name="language", type=str)
        parser.add_argument(name="conllSchema", type=dict, action="append")
        args = parser.parse_args()
        project_name =  args.projectName

        new_project_attrs: ProjectInterface = {
            "project_name": project_name,
            "description": args.description,
            "blind_annotation_mode": args.blindAnnotationMode,
            "visibility": args.visibility,
            "freezed": False,
            "config": args.config,
            "language": args.language
        }

        # KK : TODO : put all grew request in a seperated file and add error catching
        GrewService.create_project(new_project_attrs["project_name"])

        new_project = ProjectService.create(new_project_attrs)
        LastAccessService.update_last_access_per_user_and_project(
            creator_id, project_name, "write"
        )

        ProjectAccessService.create(
            {
                "user_id": creator_id,
                "project_id": new_project.id,
                "access_level": 3,
            }
        )

        default_features = ["FORM", "UPOS", "LEMMA", "MISC.Gloss"]
        default_metafeatures = ["text_en"]

        for feature in default_features:
            ProjectFeatureService.create(
                {"project_id": new_project.id, "value": feature}
            )

        for feature in default_metafeatures:
            ProjectMetaFeatureService.create(
                {"project_id": new_project.id, "value": feature}
            )
        dumped_project_config = json.dumps(args.get("conllSchema"))
        GrewService.update_project_config(project_name, dumped_project_config)

        return new_project

@api.route("/mismatch-projects")
class MistmatchProjectsResource(Resource):
    
    def get(self):
        
        projects: List[Project] = Project.query.all()
        grew_projects = GrewService.get_projects()
        grew_project_names = set([project["name"] for project in grew_projects])
        db_project_names = set([project.project_name for project in projects])
       
        diff_projects_db = db_project_names - grew_project_names
        diff_projects_grew = grew_project_names - db_project_names
    
        return { "db_projects": list(diff_projects_db), "grew_projects": list(diff_projects_grew) }    
           
@api.route("/<string:projectName>")
class ProjectIdResource(Resource):
    """Views for dealing with single identified project"""

    @responds(schema=ProjectSchemaCamel, api=api)
    def get(self, projectName: str):
        """Get a single project"""
        project = ProjectService.get_by_name(projectName)
        if project:
            return project
        else:
            abort(404, 'No such project in the backend')

    @responds(schema=ProjectSchemaCamel, api=api)
    @accepts(schema=ProjectSchemaCamel, api=api)
    def put(self, projectName: str):
        """Modify a single project (by it's name)"""
        project = ProjectService.get_by_name(projectName)
        ProjectAccessService.check_admin_access(project.id)
        changes: ProjectInterface = request.parsed_obj
        if ('project_name' in changes.keys()):
            ProjectService.rename_project(projectName, changes.get("project_name"))
            
        return ProjectService.update(project, changes)

    def delete(self, projectName: str):
        """Delete a single project (by it's name)"""
        project = ProjectService.get_by_name(projectName)
        ProjectAccessService.check_admin_access(project.id)

        project_name = ProjectService.delete_by_name(projectName)
        if project_name:
            GrewService.delete_project(project_name)
            return {"status": "Success", "projectName": project_name}
        else:
            return {
                "status": "Error",
                "message": "no project with name '{}' was found on arborator database".format(
                    project_name
                ),
            }


@api.route("/<string:projectName>/features")
class ProjectFeaturesResource(Resource):
    @responds(schema=ProjectFeaturesAndMetaSchema, api=api)
    def get(self, projectName: str):
        """Get a single project features"""
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)

        features = {
            "shown_meta": ProjectMetaFeatureService.get_by_project_id(project.id),
            "shown_features": ProjectFeatureService.get_by_project_id(project.id),
        }
        return features

    @accepts(schema=ProjectFeaturesAndMetaSchema, api=api)
    def put(self, projectName: str):
        parsed_obj: ProjectShownFeaturesAndMetaInterface = request.parsed_obj
        project = ProjectService.get_by_name(projectName)
        ProjectAccessService.check_admin_access(project.id)

        shown_features = parsed_obj.get("shown_features")
        if shown_features is not None and isinstance(shown_features, list):
            ProjectFeatureService.delete_by_project_id(project.id)
            for feature in shown_features:
                new_attrs = {"project_id": project.id, "value": feature}
                ProjectFeatureService.create(new_attrs)

        shown_meta = parsed_obj.get("shown_meta")
        if shown_meta is not None and isinstance(shown_meta, list):
            ProjectMetaFeatureService.delete_by_project_id(project.id)
            for feature in shown_meta:
                new_attrs = {"project_id": project.id, "value": feature}
                ProjectMetaFeatureService.create(new_attrs)

        return {"status": "success"}


@api.route("/<string:projectName>/conll-schema")
class ProjectConllSchemaResource(Resource):
    def get(self, projectName: str):
        """Get a single project conll schema"""
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        conll_schema = GrewService.get_conll_schema(projectName)
        return conll_schema

    def put(self, projectName: str):
        """Modify a single project conll schema"""
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        parser = reqparse.RequestParser()
        parser.add_argument(name="config", type=dict, action="append")
        args = parser.parse_args()
        dumped_project_config = json.dumps(args.config)
        GrewService.update_project_config(project.project_name, dumped_project_config)

        return {"status": "success", "message": "New conllu schema was saved"}


@api.route("/<string:projectName>/access")
class ProjectAccessResource(Resource):
    def get(self, projectName: str):
        """Get a single project users access"""
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:projectName>/access/many")
class ProjectAccessManyResource(Resource):
    def put(self, projectName: str):
        """Modify a single project users access"""
        parser = reqparse.RequestParser()
        parser.add_argument(name="selectedUsers", type=str, action="append")
        parser.add_argument(name="targetRole", type=str)
        args = parser.parse_args()
        selected_users = args.get("selectedUsers")
        target_role = args.get("targetRole")

        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        
        access_level = ProjectAccess.LABEL_TO_LEVEL[target_role]

        for username in selected_users:
        
            user_id = UserService.get_by_username(username).id
            new_attrs = {
                "user_id": user_id,
                "access_level": access_level,
                "project_id": project.id,
            }
            project_access = ProjectAccessService.get_by_user_id(user_id, project.id)
            if project_access:
                project_access = ProjectAccessService.update(project_access, new_attrs)
            else:
                project_access = ProjectAccessService.create(new_attrs)

        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:projectName>/access/<string:username>")
class ProjectAccessUserResource(Resource):
    def delete(self, projectName: str, username: str):
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        ProjectAccessService.delete(user_id, project.id)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:projectName>/image")
class ProjectImageResource(Resource):

    def get(self, projectName: str):
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(projectName)

        project_image = project.image
        if(project_image):
            image_path = os.path.join(current_app.config["PROJECT_IMAGE_FOLDER"], project_image)
            if os.path.exists(image_path):
                with open(image_path, 'rb') as file:
                    image_data = base64.b64encode(file.read()).decode('utf-8')
                    return jsonify({"image_data": image_data, "image_ext": image_path.split(".")[1]})
        return jsonify({})
    

    @responds(schema=ProjectSchemaCamel)
    def post(self, projectName: str):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "files", type=werkzeug.datastructures.FileStorage, location="files"
        )
        args = parser.parse_args()
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)

        file_ext = os.path.splitext(args["files"].filename)[1]
        if file_ext not in current_app.config["UPLOAD_IMAGE_EXTENSIONS"]:
            abort(400)

        filename = secure_filename(projectName + file_ext)
        content = args["files"].read()
        with open(
            os.path.join(current_app.config["PROJECT_IMAGE_FOLDER"], filename), "wb"
        ) as f:
            f.write(content)

        ProjectService.change_image(projectName, filename)

        return ProjectService.get_by_name(projectName)
