import os
from typing import List


from flask import abort, current_app, request
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from werkzeug.utils import secure_filename
import werkzeug

from app import db
from app.utils.grew_utils import GrewService
from app.utils.logging_utils import log_request
from app.user.service import UserService
from app.trees.service import TreeValidationService
from app.github.model import GithubCommitStatus

from .interface import ProjectExtendedInterface, ProjectInterface, ProjectShownFeaturesAndMetaInterface
from .model import Project, ProjectAccess
from .schema import ProjectExtendedSchema, ProjectSchema, ProjectFeaturesAndMetaSchema, ProjectResponseSchema
from .service import LastAccessService, ProjectAccessService, ProjectFeatureService, ProjectMetaFeatureService, ProjectService

api = Namespace("Project", description="Endpoints for dealing with projects")  # noqa

@api.route("/")

class ProjectResource(Resource):
    "Class that deals with project entity endpoints"

    @responds(schema=ProjectResponseSchema, api=api)
    def get(self)-> dict:
        """
            Get all projects in the application, in this function 
            We use two decorator one for the logs and other for the cache
        Args:
            - type(str): type of the project, can be my_projects | other_projects | all_projects | old_projects
        Returns:
            projects_list(List[projectExtendedInterface])
        """
        data = request.args

        projects_type = data.get("type")
        page = data.get("page")
        languages = data.get("languages").split(",") if data.get("languages") else None
        name = data.get("name")

        if languages is not None or name != '':
            projects = ProjectService.filter_project_by_name_or_language(name, languages)
        else:
            projects = ProjectService.get_all()

        grew_projects = GrewService.get_projects()
        extended_project_list, total_pages = ProjectService.get_projects_info(projects, grew_projects, page, 12, projects_type)
        return { "projects": extended_project_list, "total_pages": total_pages }

    @accepts(schema=ProjectSchema)
    @responds(schema=ProjectSchema)
    def post(self) -> Project:
        """Create a single Project"""
        
        if current_user.is_authenticated:
            creator_id = current_user.id
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
        else:
            abort(401, "User not loged in")

@api.route("/user-projects")
class UserProjectResource(Resource):
    "Class that deals with user projects endpoints"

    @responds(schema=ProjectExtendedSchema(many=True), api=api)
    def get(self):
        """Get user projects"""
        user = UserService.get_by_id(current_user.id)
        projects: List[Project] = Project.query.all()
        grew_projects = GrewService.get_user_projects(user.username)
        return ProjectService.get_projects_info(projects, grew_projects, 1, -1, "all_projects")[0]
      
@api.route("/mismatch-projects")
class MistmatchProjectsResource(Resource):

    def get(self):
        """
            This feature is for superdamins to help them to detect the projects 
            that exist in grew server and not in the db or projects the opposite
        Returns:
            projects_list(List[projectExtendedInterface])
        """
        projects: List[Project] = Project.query.all()
        grew_projects = GrewService.get_projects()
        grew_project_names = set([project["name"] for project in grew_projects])
        db_project_names = set([project.project_name for project in projects])
       
        diff_projects_db = db_project_names - grew_project_names
        diff_projects_grew = grew_project_names - db_project_names
    
        return { "db_projects": list(diff_projects_db), "grew_projects": list(diff_projects_grew) }    
           
@api.route("/popular-projects")
class PopularProjectsResource(Resource):
    
    @responds(schema=ProjectExtendedSchema(many=True), api=api)
    def get(self):
        """
            Get list of popular projects, projects that are active in the last 15 days
        Returns:
            projects_list(List[projectExtendedInterface])
        """
        time_ago = 15 # recent projects from 15 days 
        recent_projects = ProjectService.get_recent_projects(time_ago)
        grew_projects = GrewService.get_projects()
        
        return ProjectService.get_projects_info(recent_projects, grew_projects, 1, -1, "all_projects")[0]
        
@api.route("/<string:project_name>")
class ProjectIdResource(Resource):

    @responds(schema=ProjectSchema, api=api)
    def get(self, project_name: str):
        """Get a single project"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        ProjectService.check_if_project_exist(project)
        return project
    
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

        ProjectService.delete_by_name(project_name)
        if project_name:
            GrewService.delete_project(project_name)
            return {"": "Success", "project_name": project_name}
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
        if "shown_features" in new_shown_features_shown_meta.keys():
            shown_features = new_shown_features_shown_meta["shown_features"]
            if shown_features is not None and isinstance(shown_features, list):
                ProjectFeatureService.delete_by_project_id(project.id)
                for feature in shown_features:
                    new_attrs = {"project_id": project.id, "value": feature}
                    ProjectFeatureService.create(new_attrs)

        if "shown_meta" in new_shown_features_shown_meta.keys():
            shown_meta = new_shown_features_shown_meta["shown_meta"]
            if shown_meta is not None and isinstance(shown_meta, list):
                ProjectMetaFeatureService.delete_by_project_id(project.id)
                for feature in shown_meta:
                    new_attrs = {"project_id": project.id, "value": feature}
                    ProjectMetaFeatureService.create(new_attrs)

        return {"status": "success"}


@api.route("/<string:project_name>/conll-schema")
class ProjectConllSchemaResource(Resource):
    
    def get(self, project_name: str):
        """
        Get project conll schema
        Returns:
            - conll_schema(dict)
        """
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return GrewService.get_conll_schema(project_name)

    def put(self, project_name: str):
        """Modify project conll schema"""
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
        config = [] 
        args = request.get_json()
        update_commit = args['updateCommit']
        config.append(args['config'])
        
        if update_commit and project.github_repository: # if project synchronized changing feats and misc in the config will modify data so changes will update the commit status
            github_commit_status = GithubCommitStatus.query.filter_by(project_id=project.id).first()
            if github_commit_status:
                github_commit_status.update({"changes_number": github_commit_status.changes_number + 1})
                db.session.commit()

        GrewService.update_project_config(project.project_name, config)
        

        return {"status": "success", "message": "New conllu schema was saved"}


@api.route("/<string:project_name>/access")
class ProjectAccessResource(Resource):
    
    def get(self, project_name: str):
        """
            Get project users access
        Returns: 
            - dict(str, List[str]): list of user roles
        """
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:project_name>/access/many")
class ProjectAccessManyResource(Resource):
    
    def put(self, project_name: str):
        """
            Modify project users access
        Returns: 
            - dict(str, List[str]): list of user roles
        """
        
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
        """
            Remove project user access
        Returns: 
            - dict(str, List[str]): list of user roles
        """
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)
        
        user_id = UserService.get_by_username(username).id
        ProjectAccessService.delete(user_id, project.id)
        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:project_name>/image")
class ProjectImageResource(Resource):
    
    def get(self, project_name: str):
        """Get project image

        Args:
            project_name (str)

        Returns:
            image(str): image encoded in b64
        """
        image_path = ProjectService.get_by_name(project_name).image
        image = ProjectService.get_project_image(image_path)
        return image
    
    def post(self, project_name: str):
        """
            Update project image
        Args: 
            - files(File): image file uploaded
        """
        
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
        

@api.route("/<string:project_name>/language-detected") 
class ProjectLanguageDetectedResource(Resource):
    
    def get(self, project_name: str):
        """check if language is detected

        Args:
            project_name (str)

        Returns:
            boolean
        """
        project = ProjectService.get_by_name(project_name)
        mapped_languages = TreeValidationService.extract_ud_languages()
        return project.language in mapped_languages.keys()
        
@api.route("/languages")
class ProjectLanguagesResource(Resource):
    
    def get(self):
        """Get list of languages"""
        return [Project.language for Project in Project.query.distinct(Project.language).all()]
