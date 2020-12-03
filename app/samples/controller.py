import json
import re

from flask.helpers import send_file

from app.projects.service import ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, grew_request
from flask import Response, abort, current_app, request, send_from_directory
from flask_restx import Namespace, Resource, reqparse
# from openpyxl import Workbook

from .model import SampleRole
from .service import (
    SampleEvaluationService,
    SampleExerciseLevelService,
    SampleExportService,
    SampleRoleService,
    SampleUploadService,
)

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

        files = request.files.to_dict(flat=False).get("files")
        users_ids_convertor = {}

        for user_id_mapping in json.loads(request.form.get("usersIdsConvertor", "{}")):
            users_ids_convertor[user_id_mapping["old"]] = user_id_mapping["new"]

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
            return samples


@api.route("/<string:project_name>/samples/<string:sample_name>/role")
class SampleRoleResource(Resource):
    def post(self, project_name: str, sample_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="username", type=str)
        parser.add_argument(name="targetrole", type=str)
        parser.add_argument(name="action", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(project_name)
        project_id = project.id
        role = SampleRole.LABEL_TO_ROLES[args.targetrole]
        user_id = UserService.get_by_username(args.username).id
        if args.action == "add":
            new_attrs = {
                "project_id": project_id,
                "sample_name": sample_name,
                "user_id": user_id,
                "role": role,
            }
            SampleRoleService.create(new_attrs)

        if args.action == "remove":
            SampleRoleService.delete_one(project_id, sample_name, user_id, role)

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
        project_id = project.id

        sample_exercise_level = SampleExerciseLevelService.get_by_sample_name(
            project_id, sample_name
        )

        new_attrs = {
            "project_id": project_id,
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
        
        if evaluations:
            evaluations_tsv = SampleEvaluationService.evaluations_json_to_tsv(evaluations)

            uploadable_evaluations_tsv = SharedService.get_sendable_data(evaluations_tsv)
            
            file_name = f"{sample_name}_evaluations.tsv"
            return send_file(uploadable_evaluations_tsv, attachment_filename = file_name, as_attachment=True)
        else:
            abort(404, "No user worked on this sample")


@api.route("/<string:project_name>/samples/export")
class ExportSampleResource(Resource):
    def post(self, project_name: str):
        data = request.get_json(force=True)
        sample_names = data["samples"]
        print("requested zip", sample_names, project_name)
        sampletrees = list()
        samplecontentfiles = list()

        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":

                # {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
                sample_tree = SampleExportService.servSampleTrees(reply.get("data", {}))
                sample_content = SampleExportService.sampletree2contentfile(sample_tree)
                for sent_id in sample_tree:
                    last = SampleExportService.get_last_user(
                        sample_tree[sent_id]["conlls"]
                    )
                    sample_content["last"] = sample_content.get("last", []) + [
                        sample_tree[sent_id]["conlls"][last]
                    ]

                # gluing back the trees
                sample_content["last"] = "\n".join(sample_content["last"])
                samplecontentfiles.append(sample_content)

            else:
                print("Error: {}".format(reply.get("message")))

        memory_file = SampleExportService.contentfiles2zip(
            sample_names, samplecontentfiles
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
        ProjectService.check_if_project_exist(project)
        GrewService.delete_sample(project_name, sample_name)
        SampleRoleService.delete_by_sample_name(project.id, sample_name)
        SampleExerciseLevelService.delete_by_sample_name(project.id, sample_name)
        return {
            "status": "OK",
        }
