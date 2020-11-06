import json
import re

from app.projects.service import ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, grew_request
from flask import Response, abort, current_app, request
from flask_restx import Namespace, Resource, reqparse

from .model import SampleRole
from .service import (SampleExerciseLevelService, SampleExportService,
                      SampleRoleService, SampleUploadService)

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
        for sa in grew_samples:
            sample = {
                "sample_name": sa["name"],
                "sentences": sa["number_sentences"],
                "number_trees": sa["number_trees"],
                "tokens": sa["number_tokens"],
                "treesFrom": sa["users"],
                "roles": {},
            }
            sample["roles"] = SampleRoleService.get_by_sample_name(
                project.id, sa["name"]
            )
            sample_exercise_level = SampleExerciseLevelService.get_by_sample_name(
                project.id, sa["name"]
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

        fichiers = request.files.to_dict(flat=False).get("files")
        users_ids_convertor = {}

        for user_id_mapping in json.loads(request.form.get("usersIdsConvertor", "{}")):
            users_ids_convertor[user_id_mapping["old"]] = user_id_mapping["new"]

        if fichiers:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")
            grew_samples = GrewService.get_samples(project_name)
            samples_names = [sa["name"] for sa in grew_samples]

            for f in fichiers:
                status, message = SampleUploadService.upload(
                    f,
                    project_name,
                    reextensions=reextensions,
                    existing_samples=samples_names,
                    users_ids_convertor=users_ids_convertor,
                )
                if status != 200:
                    resp = {"status": status, "message": message}
                    return resp

            # samples = {"samples": project_service.get_samples(project_name)}
            samples = {"samples": "success"}
            return samples


@api.route("/<string:project_name>/samples/<string:sampleName>/role")
class SampleRoleResource(Resource):
    def post(self, project_name: str, sampleName: str):
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
                "sample_name": sampleName,
                "user_id": user_id,
                "role": role,
            }
            SampleRoleService.create(new_attrs)

        if args.action == "remove":
            SampleRoleService.delete_one(project_id, sampleName, user_id, role)

        data = {
            "roles": SampleRoleService.get_by_sample_name(project.id, sampleName),
        }
        return data


@api.route("/<string:project_name>/samples/<string:sampleName>/exercise-level")
class SampleExerciseLevelResource(Resource):
    def post(self, project_name: str, sampleName: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="exerciseLevel", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(project_name)
        project_id = project.id

        sample_exercise_level = SampleExerciseLevelService.get_by_sample_name(
            project_id, sampleName
        )

        new_attrs = {
            "project_id": project_id,
            "sample_name": sampleName,
            "exercise_level": args.exerciseLevel,
        }

        if sample_exercise_level:
            SampleExerciseLevelService.update(sample_exercise_level, new_attrs)
        else:
            SampleExerciseLevelService.create(new_attrs)

        return {"status": "success"}


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

        grew_request(
            "eraseSample",
            data={"project_id": project_name, "sample_id": sample_name},
        )
        SampleRoleService.delete_by_sample_name(project.id, sample_name)
        SampleExerciseLevelService.delete_by_sample_name(project.id, sample_name)
        return {
            "status": "OK",
        }
