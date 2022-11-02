import json, re, datetime, time, os
from typing import List
from sqlalchemy.sql.functions import user

import werkzeug
from werkzeug.utils import secure_filename
from app.utils.grew_utils import GrewService
from flask import abort, current_app, request, session
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

from .interface import ProjectExtendedInterface, ProjectInterface
from .model import Project, ProjectAccess
from .schema import ProjectExtendedSchema, ProjectSchema, ProjectSchemaCamel
from .service import (
    LastAccessService,
    ProjectAccessService,
    ProjectFeatureService,
    ProjectMetaFeatureService,
    ProjectService,
)

api = Namespace("Project", description="Endpoints for dealing with projects")  # noqa
# appconfig = current_app.config

@api.route("/")
class ProjectResource(Resource):
    "Project"

    @responds(schema=ProjectExtendedSchema(many=True), api=api)
    def get(self) -> List[ProjectExtendedInterface]:
        """Get all projects"""

        projects_extended_list: List[ProjectExtendedInterface] = []
        push_project = projects_extended_list.append

        projects: List[Project] = Project.query.all()
        
        grew_projects = GrewService.get_projects()

        grewnames = set([project["name"] for project in grew_projects])
        dbnames = set([project.project_name for project in projects])
        common = grewnames & dbnames

        for project in projects:
            dumped_project: ProjectExtendedInterface = ProjectSchema().dump(project)
            if dumped_project["project_name"] not in common: continue

            dumped_project["admins"], dumped_project["guests"] = ProjectAccessService.get_all(project.id)

            # better version: less complexity + database calls / 2
            last_access, last_write_access = LastAccessService.get_last_access_time_per_project(project.project_name, "any+write")
            now = datetime.datetime.now().timestamp()
            dumped_project["last_access"] = last_access - now
            dumped_project["last_write_access"] = last_write_access - now

            for p in grew_projects:
                if p["name"] == project.project_name:
                    dumped_project["number_sentences"] = p["number_sentences"]
                    dumped_project["number_samples"] = p["number_samples"]
                    dumped_project["number_tokens"] = p["number_tokens"]
                    dumped_project["number_trees"] = p["number_trees"]
            push_project(dumped_project)

        return projects_extended_list

    # @accepts(
    #     dict(name="project_name", type=str),
    #     # dict(name="user", type=str),
    #     # dict(name="description", type=str),
    #     # dict(name="name", type=str),
    #     # dict(name="showAllTrees", type=bool),
    #     # dict(name="user", type=str),
    #     # dict(name="visibility", type=int),
    #     # dict(name="exerciseMode", type=bool),
    #     # schema=ProjectSchema,
    #     api=api,
    # )
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
        parser.add_argument(name="showAllTrees", type=bool)
        parser.add_argument(name="exerciseMode", type=bool)
        parser.add_argument(name="visibility", type=int)
        args = parser.parse_args()
        
        # Sanitize the project name to correspond to Grew folders requirements
        projectName = re.sub('[^0-9\w]+', '_', args.projectName)

        new_project_attrs: ProjectInterface = {
            "project_name": projectName,
            "description": args.description,
            "show_all_trees": args.showAllTrees,
            "exercise_mode": args.exerciseMode,
            "visibility": args.visibility,
        }

        # KK : TODO : put all grew request in a seperated file and add error catching
        GrewService.create_project(new_project_attrs["project_name"])

        new_project = ProjectService.create(new_project_attrs)
        LastAccessService.update_last_access_per_user_and_project(creator_id, projectName, "write")

        ProjectAccessService.create(
            {
                "user_id": creator_id,
                "project_id": new_project.id,
                "access_level": 2,
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

        return new_project
        # return ProjectService.create(request.parsed_obj)


@api.route("/<string:projectName>")
class ProjectIdResource(Resource):
    """Views for dealing with single identified project"""

    @responds(schema=ProjectSchemaCamel, api=api)
    def get(self, projectName: str):
        """Get a single project"""
        return ProjectService.get_by_name(projectName)

    @responds(schema=ProjectSchemaCamel, api=api)
    @accepts(schema=ProjectSchemaCamel, api=api)
    def put(self, projectName: str):
        """Modify a single project (by it's name)"""
        project = ProjectService.get_by_name(projectName)
        
        ProjectAccessService.check_admin_access(project.id)

        changes: ProjectInterface = request.parsed_obj
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
    def get(self, projectName: str):
        """Get a single project features"""
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)


        features = {
            # TODO : On frontend and backend, It's absolutely necessary to uniformize naming conventions and orthography
            # ... we should have "shownMeta" /"shownFeatues" or "shownMeta"/"shownFeature"
            "shownmeta": ProjectMetaFeatureService.get_by_project_id(project.id),
            "shownfeatures": ProjectFeatureService.get_by_project_id(project.id),
        }
        return features

    def put(self, projectName: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="shownfeatures", type=str, action="append")
        parser.add_argument(name="shownmeta", type=str, action="append")
        args = parser.parse_args()
        project = ProjectService.get_by_name(projectName)
        if args.get("shownfeatures"):
            ProjectFeatureService.delete_by_project_id(project.id)
            for feature in args.shownfeatures:
                new_attrs = {"project_id": project.id, "value": feature}
                ProjectFeatureService.create(new_attrs)

        if args.get("shownmeta"):
            ProjectMetaFeatureService.delete_by_project_id(project.id)
            for feature in args.shownmeta:
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
        parser.add_argument(name="user_ids", type=str, action="append")
        parser.add_argument(name="targetrole", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)

        access_level = ProjectAccess.LABEL_TO_LEVEL[args.targetrole]

        for user_id in args.user_ids:
            # TODO : add interface to new_attrs
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


@api.route("/<string:projectName>/access/<string:userId>")
class ProjectAccessUserResource(Resource):
    def delete(self, projectName: str, userId: str):
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.delete(userId, project.id)

        return ProjectAccessService.get_users_role(project.id)


# @api.route("/<string:projectName>/image")
# class ProjectImageResource(Resource):
#     @responds(schema=ProjectSchemaCamel)
#     def post(self, projectName: str):
#         parser = reqparse.RequestParser()
#         parser.add_argument(
#             "files", type=werkzeug.datastructures.FileStorage, location="files"
#         )
#         args = parser.parse_args()
#         project = ProjectService.get_by_name(projectName)
#         ProjectService.check_if_project_exist(project)

#         content = args["files"].read()
#         ProjectService.change_image(projectName, content)
#         return ProjectService.get_by_name(projectName)


@api.route("/<string:projectName>/image")
class ProjectImageResource(Resource):
    @responds(schema=ProjectSchemaCamel)
    def post(self, projectName: str):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "files", type=werkzeug.datastructures.FileStorage, location="files"
        )
        args = parser.parse_args()
        project = ProjectService.get_by_name(projectName)
        ProjectService.check_if_project_exist(project)
        
        file_ext = os.path.splitext(args['files'].filename)[1]
        if file_ext not in current_app.config['UPLOAD_IMAGE_EXTENSIONS']:
            abort(400)
        
        filename = secure_filename(projectName+file_ext)
        # uploaded_file.save(os.path.join(current_app.config['PROJECT_IMAGE_FOLDER'], filename))
        content = args["files"].read()
        with open(os.path.join(current_app.config['PROJECT_IMAGE_FOLDER'], filename), 'wb') as f:
            f.write(content)
        
        filepath = 'images/projectimages/%s' % (filename)
        ProjectService.change_image(projectName, filepath)

        return ProjectService.get_by_name(projectName)


@api.route("/last_access")
class LastAccessController(Resource):
    @responds()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument(name="projectName", type=str)
        parser.add_argument(name="username", type=str)
        parser.add_argument(name="accessType", type=str)
        args = parser.parse_args()

        project_name = args.projectName
        username = args.username
        access_type = args.accessType or "any"
        
        if project_name == None and username == None:
            abort(400) # TODO : FIXME please : more logging or info returned to the FE (frontend)
        
        if project_name and username:
            return LastAccessService.get_last_access_time_per_user_and_project(username, project_name, access_type)

        if project_name:
            return LastAccessService.get_last_access_time_per_project(project_name, access_type)
        if username:
            return LastAccessService.get_last_access_time_per_user(username, access_type)



# @api.route('/<string:projectName>/settings_info')
# class ProjectSettingsInfoResource(Resource):
#     def get(self, projectName: str):
#         return ProjectService.get_settings_infos(
#             projectName, current_user
#         )
