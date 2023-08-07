import json
import re

from flask.helpers import send_file
from flask import Response, request
from flask_restx import Namespace, Resource, reqparse
from flask_login import current_user

from app.projects.service import ProjectAccessService, ProjectService, LastAccessService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, SampleExportService, grew_request

from .service import (
    SampleEvaluationService,
    SampleExerciseLevelService,
    SampleUploadService,
    SampleTokenizeService,
)

api = Namespace(
    "Samples", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/samples")
class SampleResource(Resource):
    "Samples"

    def get(self, project_name: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        grew_samples = GrewService.get_samples(project_name)

        processed_samples = []
        for grew_sample in grew_samples:
            sample = {
                "sample_name": grew_sample["name"],
                "sentences": grew_sample["number_sentences"],
                "number_trees": grew_sample["number_trees"],
                "tokens": grew_sample["number_tokens"],
                "treesFrom": grew_sample["users"],
                "treeByUser": grew_sample["tree_by_user"],
                "roles": {},
            }
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
        ProjectService.check_if_freezed(project)
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
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
            return {"status": "OK"}
        
@api.route("/<string:project_name>/samples/tokenize")
class SampleTokenizeResource(Resource):
    def post(self, project_name):
        parser = reqparse.RequestParser()
        parser.add_argument(name="username", type=str)
        parser.add_argument(name="sampleName", type=str)
        parser.add_argument(name="option", type=str)
        parser.add_argument(name="lang", type=str)
        parser.add_argument(name="text", type=str)

        args = parser.parse_args()
        username = args.get("username")
        sample_name = args.get("sampleName")
        option = args.get("option")
        lang = args.get("lang")
        text = args.get("text")
        SampleTokenizeService.tokenize(text, option, lang, project_name, sample_name, username)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


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


        parser = reqparse.RequestParser()
        parser.add_argument("sampleNames", type=str, action="append")
        parser.add_argument("users", type=str, action="append")
        args = parser.parse_args()
        sample_names = args.get("sampleNames")
        users = args.get("users")
        sample_names, samples_with_string_content = GrewService.get_samples_with_string_contents(project_name, sample_names)

        memory_file = SampleExportService.contentfiles2zip(
            sample_names, samples_with_string_content, users
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
        ProjectService.check_if_freezed(project)
        ProjectService.check_if_project_exist(project)
        GrewService.delete_sample(project_name, sample_name)
        SampleExerciseLevelService.delete_by_sample_name(project.id, sample_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return {
            "status": "OK",
        }

