import json
import os
import re
import requests

from flask.helpers import send_file

from app import parser_config
from app.projects.service import ProjectAccessService, ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, SampleExportService, grew_request
from app.config import Config
from flask import Response, abort, current_app, request, send_from_directory
from flask_restx import Namespace, Resource, reqparse

from .model import SampleRole
from .service import (
    SampleEvaluationService,
    SampleExerciseLevelService,
    SampleRoleService,
    SampleUploadService,
    add_or_keep_timestamps, add_or_replace_userid,
)
from ..utils.arborator_parser_utils import ArboratorParserAPI

api = Namespace(
    "Samples", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/samples")
class SampleResource(Resource):
    "Samples"

    def get(self, project_name: str):
        project = ProjectService.get_by_name(project_name)
        grew_samples = GrewService.get_samples(project_name)

        processed_samples = []
        for grew_sample in grew_samples:
            sample = {
                "sample_name": grew_sample["name"],
                "sentences": grew_sample["number_sentences"],
                "number_trees": grew_sample["number_trees"],
                "tokens": grew_sample["number_tokens"],
                "treesFrom": grew_sample["users"],
                "roles": {},
            }
            sample["roles"] = SampleRoleService.get_by_sample_name(
                project.id, grew_sample["name"]
            )
            sample_exercise_level = SampleExerciseLevelService.get_by_sample_name(
                project.id, grew_sample["name"]
            )
            if sample_exercise_level:
                sample["exerciseLevel"] = sample_exercise_level.exercise_level.code
            else:
                sample["exerciseLevel"] = 4

            processed_samples.append(sample)
        return processed_samples

    def post(self, project_name: str):
        """Upload a sample to the server"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)

        users_ids_convertor = {}
        for user_id_mapping in json.loads(request.form.get("userIdsConvertor", "{}")):
            users_ids_convertor[user_id_mapping["old"]] = user_id_mapping["new"]
            
        files = request.files.to_dict(flat=False).get("files")
        if files:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")
            grew_samples = GrewService.get_samples(project_name)
            samples_names = [sa["name"] for sa in grew_samples]

            for file in files:
                SampleUploadService.upload(
                    file,
                    project_name,
                    reextensions=reextensions,
                    existing_samples=samples_names,
                    users_ids_convertor=users_ids_convertor,
                )
            # samples = {"samples": Sam.get_samples(project_name)}
            return {"status": "OK"}


@api.route("/<string:project_name>/samples/<string:sample_name>/role")
class SampleRoleResource(Resource):
    def post(self, project_name: str, sample_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="username", type=str)
        parser.add_argument(name="targetrole", type=str)
        parser.add_argument(name="action", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)

        role = SampleRole.LABEL_TO_ROLES[args.targetrole]
        user_id = UserService.get_by_username(args.username).id
        if args.action == "add":
            new_attrs = {
                "project_id": project.id,
                "sample_name": sample_name,
                "user_id": user_id,
                "role": role,
            }
            SampleRoleService.create(new_attrs)

        if args.action == "remove":
            SampleRoleService.delete_one(project.id, sample_name, user_id, role)

        data = {
            "roles": SampleRoleService.get_by_sample_name(project.id, sample_name),
        }
        return data


@api.route("/<string:project_name>/samples/<string:sample_name>/exercise-level")
class SampleExerciseLevelResource(Resource):
    def post(self, project_name: str, sample_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="exerciseLevel", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)

        sample_exercise_level = SampleExerciseLevelService.get_by_sample_name(
            project.id, sample_name
        )

        new_attrs = {
            "project_id": project.id,
            "sample_name": sample_name,
            "exercise_level": args.exerciseLevel,
        }

        if sample_exercise_level:
            SampleExerciseLevelService.update(sample_exercise_level, new_attrs)
        else:
            SampleExerciseLevelService.create(new_attrs)

        return {"status": "success"}
from app.shared.service import SharedService

@api.route("/<string:project_name>/samples/<string:sample_name>/evaluation")
class SampleEvaluationResource(Resource):
    def get(self, project_name, sample_name):
        sample_conlls = GrewService.get_sample_trees(project_name, sample_name)
        evaluations = SampleEvaluationService.evaluate_sample(sample_conlls)
        evaluations_tsv = SampleEvaluationService.evaluations_json_to_tsv(evaluations)
        uploadable_evaluations_tsv = SharedService.get_sendable_data(evaluations_tsv)
        file_name = f"{sample_name}_evaluations.tsv"
        return send_file(uploadable_evaluations_tsv, attachment_filename = file_name, as_attachment=True)


@api.route("/<string:project_name>/samples/export")
class ExportSampleResource(Resource):
    def post(self, project_name: str):
        data = request.get_json(force=True)
        sample_names = data["samples"]
        print("requested zip", sample_names, project_name)
        
        sample_names, samples_with_string_content = GrewService.get_samples_with_string_contents(project_name, sample_names)

        memory_file = SampleExportService.contentfiles2zip(
            sample_names, samples_with_string_content
        )

        resp = Response(
            memory_file,
            status=200,
            mimetype="application/zip",
            headers={
                "Content-Disposition": "attachment;filename=dump.{}.zip".format(
                    project_name
                )
            },
        )
        return resp

@api.route("/<string:project_name>/samples/<string:sample_name>")
class DeleteSampleResource(Resource):
    def delete(self, project_name: str, sample_name: str):
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        ProjectService.check_if_project_exist(project)
        GrewService.delete_sample(project_name, sample_name)
        SampleRoleService.delete_by_sample_name(project.id, sample_name)
        SampleExerciseLevelService.delete_by_sample_name(project.id, sample_name)
        return {
            "status": "OK",
        }



@api.route("/<string:project_name>/samples/parser/train/start")
class ParserTrainStartResource(Resource):
    def post(self, project_name):
        if project_name == "undefined":
            return {"status" : "NOT VALID PROJECT NAME"}

        params = request.get_json(force=True)
        print("<PARSER> train/start request :", params)
        train_samples_names = params["train_samples_names"]
        train_user = params["train_user"]
        max_epoch = params["max_epoch"]

        train_samples = GrewService.get_samples_with_string_contents_as_dict(project_name, train_samples_names, train_user)

        return ArboratorParserAPI.train_start(project_name, train_samples, max_epoch)



@api.route("/<string:project_name>/samples/parser/train/status")
class ParserTrainStatusResource(Resource):
    def post(self, project_name):
        if project_name == "undefined":
            return {"status": "NOT VALID PROJECT NAME"}

        params = request.get_json(force=True)
        print("<PARSER> parser/info request :", params)

        model_info = params["model_info"]
        model_id = model_info["model_id"]

        return ArboratorParserAPI.train_status(project_name, model_id)



@api.route("/<string:project_name>/samples/parser/parse/start")
class ParserParseStartResource(Resource):
    def post(self, project_name):
        if project_name == "undefined":
            return {"status" : "NOT VALID PROJECT NAME"}
        params = request.get_json(force=True)
        print("<PARSER> parse/start request :", params)

        to_parse_samples_names = params["to_parse_samples_names"]
        model_id = params["model_id"]

        to_parse_samples = GrewService.get_samples_with_string_contents_as_dict(project_name, to_parse_samples_names, "last")

        return ArboratorParserAPI.parse_start(project_name, model_id, to_parse_samples)


@api.route("/<string:project_name>/samples/parser/parse/status")
class ParserParseStatus(Resource):
    def post(self, project_name):
        if project_name == "undefined":
            return {"status": "NOT VALID PROJECT NAME"}
        params = request.get_json(force=True)
        print("<PARSER> parse/status request :", params)
        model_id = params["model_id"]
        parse_task_id = params["parse_task_id"]
        parser_suffix = params["parser_suffix"]

        parse_status_reply = ArboratorParserAPI.parse_status(parse_task_id)
        if parse_status_reply["status"] == "failure":
            return parse_status_reply

        else:
            data = parse_status_reply["data"]
            if data["ready"]:
                task_model_info = data["result"]["model_info"]
                task_parsed_samples = data["result"]["parsed_samples"]

                if task_model_info["model_id"] == model_id and task_model_info["project_name"] == project_name:

                    for sample_name, sample_content in task_parsed_samples.items():
                        path_file = os.path.join(Config.UPLOAD_FOLDER, sample_name)
                        print('upload parsed\n', path_file)
                        with open(path_file,'w') as f:
                            f.write(sample_content)

                        add_or_keep_timestamps(path_file, when="long_ago")
                        add_or_replace_userid(path_file, "parser" + parser_suffix)
                        print("KK GREW SAVING", "parser" + parser_suffix)
                        with open(path_file, "rb") as file_to_save:
                            print('save files')
                            GrewService.save_sample(project_name, sample_name, file_to_save)

                    return {"status": "success", "data": {"ready": True, "model_info": task_model_info}}
            else:
                return {"status": "success", "data": {"ready": False}}

            return {"status": "failure", "error": "unknown error in ParserParseStatus"}




