import datetime
import json
import os
from typing import List


from flask import abort, current_app, request
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from werkzeug.utils import secure_filename
import werkzeug

from app.utils.grew_utils import GrewService
from app.user.service import UserService

from .interface import ProjectExtendedInterface, ProjectInterface, ProjectShownFeaturesAndMetaInterface
from .model import Project, ProjectAccess
from .schema import ProjectExtendedSchema, ProjectSchema, ProjectFeaturesAndMetaSchema
from .service import LastAccessService, ProjectAccessService, ProjectFeatureService, ProjectMetaFeatureService, ProjectService

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

        grew_projects_names = set([project["name"] for project in grew_projects])
        db_projects_names = set([project.project_name for project in projects])
        common = grew_projects_names & db_projects_names

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
                
                project.owner_avatar_url = UserService.get_by_username(project.admins[0]).picture_url
                
                (
                    last_access,
                    last_write_access,
                ) = LastAccessService.get_project_last_access(
                    project.project_name
                )
                now = datetime.datetime.now().timestamp()
                project.last_access = last_access - now
                project.last_write_access = last_write_access - now

                project_path = project.image
                project.image = ProjectService.get_project_image(project_path)
               
                for grew_project in grew_projects:
                    if grew_project["name"] == project.project_name:
                        project.users = grew_project["users"]
                        project.number_sentences = grew_project["number_sentences"]
                        project.number_samples = grew_project["number_samples"]
                        project.number_tokens = grew_project["number_tokens"]
                        project.number_trees = grew_project["number_trees"]
                projects_extended_list.append(project)

        return projects_extended_list
    
    @accepts(schema=ProjectSchema)
    @responds(schema=ProjectSchema)
    def post(self) -> Project:
        """Create a single Project"""
        
        try:
            creator_id = current_user.id
        except:
            abort(401, "User not loged in")
            raise
        
        new_project_attrs: ProjectInterface = request.parsed_obj

        GrewService.create_project(new_project_attrs["project_name"])
        new_project = ProjectService.create(new_project_attrs)
        
        LastAccessService.update_last_access_per_user_and_project(
            creator_id, new_project_attrs["project_name"], "write"
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
            ProjectFeatureService.create({"project_id": new_project.id, "value": feature})

        for feature in default_metafeatures:
            ProjectMetaFeatureService.create({"project_id": new_project.id, "value": feature})

        return new_project


@api.route("/<string:project_name>")
class ProjectIdResource(Resource):

    @responds(schema=ProjectSchema, api=api)
    def get(self, project_name: str):
        """Get a single project"""
        project = ProjectService.get_by_name(project_name)
        if project:
            return project
        else:
            abort(404, 'No such project in the backend')

    @responds(schema=ProjectSchema, api=api)
    @accepts(schema=ProjectSchema, api=api)
    def put(self, project_name: str):
        """Modify a project (by it's name)"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        
        changes: ProjectInterface = request.parsed_obj
        if 'project_name' in changes.keys():
            GrewService.rename_project(project_name, changes.get("project_name"))  
        return ProjectService.update(project, changes)

    def delete(self, project_name: str):
        """Delete a project (by it's name)"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)

        project_name = ProjectService.delete_by_name(project_name)
        if project_name:
            GrewService.delete_project(project_name)
            return {"status": "Success", "project_name": project_name}
        else:
            return {
                "status": "Error",
                "message": "no project with name '{}' was found on arborator database".format(
                    project_name
                ),
            }


@api.route("/<string:project_name>/features")
class ProjectFeaturesResource(Resource):
    """Class for dealing with project features"""
    
    @responds(schema=ProjectFeaturesAndMetaSchema, api=api)
    def get(self, project_name: str):
        """Get project features"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)

        features = {
            "shown_meta": ProjectMetaFeatureService.get_by_project_id(project.id),
            "shown_features": ProjectFeatureService.get_by_project_id(project.id),
        }
        return features

    @accepts(schema=ProjectFeaturesAndMetaSchema, api=api)
    def put(self, project_name: str):
        """Update project features"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
        new_shown_features_shown_meta: ProjectShownFeaturesAndMetaInterface = request.parsed_obj
        shown_features = new_shown_features_shown_meta["shown_features"]
        if shown_features is not None and isinstance(shown_features, list):
            ProjectFeatureService.delete_by_project_id(project.id)
            for feature in shown_features:
                new_attrs = {"project_id": project.id, "value": feature}
                ProjectFeatureService.create(new_attrs)

        shown_meta = new_shown_features_shown_meta["shown_features"]
        if shown_meta is not None and isinstance(shown_meta, list):
            ProjectMetaFeatureService.delete_by_project_id(project.id)
            for feature in shown_meta:
                new_attrs = {"project_id": project.id, "value": feature}
                ProjectMetaFeatureService.create(new_attrs)

        return {"status": "success"}


@api.route("/<string:project_name>/conll-schema")
class ProjectConllSchemaResource(Resource):
    
    def get(self, project_name: str):
        """Get project conll schema"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return GrewService.get_conll_schema(project_name)

    def put(self, project_name: str):
        """Modify project conll schema"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
        args = request.get_json()
        dumped_project_config = json.dumps(args.config)
        GrewService.update_project_config(project.project_name, dumped_project_config)

        return {"status": "success", "message": "New conllu schema was saved"}


@api.route("/<string:project_name>/access")
class ProjectAccessResource(Resource):
    
    def get(self, project_name: str):
        """Get project users access"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:project_name>/access/many")
class ProjectAccessManyResource(Resource):
    
    def put(self, project_name: str):
        """Modify project users access"""
        
        args = request.get_json()
        selected_users = args["selectedUsers"]
        target_role = args["targetRole"]

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
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
                ProjectAccessService.update(project_access, new_attrs)
            else:
                ProjectAccessService.create(new_attrs)

        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:project_name>/access/<string:username>")
class ProjectAccessUserResource(Resource):
    
    def delete(self, project_name: str, username: str):
        """Remove project user access"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
        user_id = UserService.get_by_username(username).id
        ProjectAccessService.delete(user_id, project.id)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:project_name>/image")
class ProjectImageResource(Resource):
    
    def get(self, project_name: str):
        
        image_path = ProjectService.get_by_name(project_name).image
        image = ProjectService.get_project_image(image_path)
        return image
    
    def post(self, project_name: str):
        """Update project image"""
        
        parser = reqparse.RequestParser()
        parser.add_argument("files", type=werkzeug.datastructures.FileStorage, location="files")
        args = parser.parse_args()
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
         
        file_extension = os.path.splitext(args["files"].filename)[1]
        if file_extension not in current_app.config["UPLOAD_IMAGE_EXTENSIONS"]:
            abort(400)

        file_name = secure_filename(project_name + file_extension)
        content = args["files"].read()
        with open(os.path.join(current_app.config["PROJECT_IMAGE_FOLDER"], file_name), "wb") as f:
            f.write(content)
        ProjectService.update(project, {"image": file_name})
        
