import json
from typing import List

import werkzeug
from app.utils.grew_utils import grew_request
from flask import abort, current_app, request
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

from .interface import ProjectExtendedInterface, ProjectInterface
from .model import Project, ProjectAccess
from .schema import ProjectExtendedSchema, ProjectSchema, ProjectSchemaCamel
from .service import (ProjectAccessService, ProjectFeatureService,
                      ProjectMetaFeatureService, ProjectService)

api = Namespace("Project", description="Endpoints for dealing with projects")  # noqa


@api.route("/")
class ProjectResource(Resource):
    "Project"

    @responds(schema=ProjectExtendedSchema(many=True), api=api)
    def get(self) -> List[ProjectExtendedInterface]:
        """Get all projects"""
        # return [{"id":4, "project_name":"yolo"}, {"id":5, "project_name":"yolo"}]
        # projects_info = {"difference": False, "projects": list()}
        projects_extended_list: List[ProjectExtendedInterface] = []
        projects: List[Project] = Project.query.all()
        reply = grew_request("getProjects", current_app)
        if not reply:
            return []
        data = reply["data"]
        grewnames = set([project["name"] for project in data])
        dbnames = set([project.project_name for project in projects])
        common = grewnames & dbnames
        # if len(grewnames ^ dbnames) > 0:
        # projects_info["difference"] = True
        for project in projects:
            dumped_project: ProjectExtendedInterface = ProjectSchema().dump(project)
            if dumped_project["project_name"] not in common:
                continue
            # admins = [a.user_id for a in project_dao.get_admins(project.id)]
            # guests = [g.user_id for g in project_dao.get_guests(project.id)]
            #     projectJson = project.as_json(include={"admins": admins, "guests": guests})
            dumped_project["admins"] = ProjectAccessService.get_admins(
                project.id)
            dumped_project["guests"] = ProjectAccessService.get_guests(
                project.id)

            for p in data:
                if p["name"] == project.project_name:
                    dumped_project["number_sentences"] = p["number_sentences"]
                    dumped_project["number_samples"] = p["number_samples"]
                    dumped_project["number_tokens"] = p["number_tokens"]
                    dumped_project["number_trees"] = p["number_trees"]
            projects_extended_list.append(dumped_project)

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
        new_project_attrs: ProjectInterface = {
            "project_name": args.projectName,
            "description": args.description,
            "show_all_trees": args.showAllTrees,
            "exercise_mode": args.exerciseMode,
            "visibility": args.visibility,
        }

        # KK : TODO : put all grew request in a seperated file and add error catching
        new_project_grew = grew_request(
            "newProject",
            current_app,
            data={"project_id": new_project_attrs["project_name"]},
        )

        new_project = ProjectService.create(new_project_attrs)
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
        print("KK request.parsed_obj", request.parsed_obj)
        changes: ProjectInterface = request.parsed_obj
        project = ProjectService.get_by_name(projectName)

        return ProjectService.update(project, changes)

    def delete(self, projectName: str):
        """Delete a single project (by it's name)"""
        project_name = ProjectService.delete_by_name(projectName)
        if project_name:
            grew_request("eraseProject", current_app,
                         data={"project_id": project_name})
        return {"status": "Success", "projectName": project_name}


@api.route("/<string:projectName>/features")
class ProjectFeaturesResource(Resource):
    def get(self, projectName: str):
        """Get a single project features"""
        project = ProjectService.get_by_name(projectName)
        if not project:
            # TODO : Create our own custom errorhandler (the following code is present at least 6 times !)
            return {
                "status": "failed",
                "message": "There was no project `{}` stored on grew".format(
                    projectName
                ),
            }

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
        if not project:
            return {
                "status": "failed",
                "message": "There was no project `{}` stored on grew".format(
                    projectName
                ),
            }
        grew_reply = grew_request(
            "getProjectConfig", current_app, data={"project_id": project.project_name}
        )
        # TODO : redo this. It's ugly
        data = grew_reply.get("data")
        if data:
            conll_schema = {
                # be careful, grew_reply["data"] is a list of object. See why, and add an interface for GREW !!
                "annotationFeatures": data[0],
            }
        else:
            conll_schema = {}
        return conll_schema

    def put(self, projectName: str):
        """Modify a single project conll schema"""
        project = ProjectService.get_by_name(projectName)
        parser = reqparse.RequestParser()
        parser.add_argument(name="config", type=dict, action="append")
        args = parser.parse_args()
        reply = grew_request(
            "updateProjectConfig",
            current_app,
            data={
                "project_id": project.project_name,
                "config": json.dumps(args.config),
            },
        )
        return {"status": "success", "message": "New conllu schema was saved"}


@api.route("/<string:projectName>/access")
class ProjectAccessResource(Resource):
    def get(self, projectName: str):
        """Get a single project users access"""
        project = ProjectService.get_by_name(projectName)
        if not project:
            return {
                "status": "failed",
                "message": "There was no project `{}` stored on grew".format(
                    projectName
                ),
            }

        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:projectName>/access/many")
class ProjectAccessManyResource(Resource):
    def put(self, projectName: str):
        """Get a single project users access"""
        parser = reqparse.RequestParser()
        parser.add_argument(name="user_ids", type=str, action="append")
        parser.add_argument(name="targetrole", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(projectName)
        if not project:
            return {
                "status": "failed",
                "message": "There was no project `{}` stored on grew".format(
                    projectName
                ),
            }
        access_level = ProjectAccess.LABEL_TO_LEVEL[args.targetrole]

        for user_id in args.user_ids:
            # TODO : add interface to new_attrs
            new_attrs = {
                "user_id": user_id,
                "access_level": access_level,
                "project_id": project.id,
            }
            project_access = ProjectAccessService.get_by_user_id(
                user_id, project.id)
            if project_access:
                project_access = ProjectAccessService.update(
                    project_access, new_attrs)
            else:
                project_access = ProjectAccessService.create(new_attrs)

        return ProjectAccessService.get_users_role(project.id)


@api.route("/<string:projectName>/access/<string:userId>")
class ProjectAccessUserResource(Resource):
    def delete(self, projectName: str, userId: str):
        project = ProjectService.get_by_name(projectName)
        if not project:
            return {
                "status": "failed",
                "message": "There was no project `{}` stored on grew".format(
                    projectName
                ),
            }

        ProjectAccessService.delete(userId, project.id)

        return ProjectAccessService.get_users_role(project.id)


@api.route('/<string:projectName>/image')
class ProjectImageResource(Resource):
    @responds(schema=ProjectSchemaCamel)
    def post(self, projectName: str):
        print('KK heey')
        parser = reqparse.RequestParser()
        parser.add_argument(
            'files', type=werkzeug.datastructures.FileStorage, location='files')
        args = parser.parse_args()
        print('KK image', args['files'])
        project = ProjectService.get_by_name(projectName)
        if not project:
            abort(400)
        content = args['files'].read()
        ProjectService.change_image(projectName, content)
        return ProjectService.get_by_name(projectName)

# @api.route('/<string:projectName>/settings_info')
# class ProjectSettingsInfoResource(Resource):
#     def get(self, projectName: str):
#         return ProjectService.get_settings_infos(
#             projectName, current_user
#         )
