from importlib.resources import path
import json
import os
import re
import requests 

from flask.helpers import send_file

from app.projects.service import ProjectAccessService, ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, SampleExportService, grew_request
from app.config import Config
from flask import Response, abort, current_app, request, send_from_directory
from flask_restx import Namespace, Resource, reqparse
# from openpyxl import Workbook

from .model import SampleRole
from .service import (
    SampleEvaluationService,
    SampleExerciseLevelService,
    SampleRoleService,
    SampleUploadService,
    add_or_keep_timestamps,
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

@api.route("/<string:project_name>/samples/parsing", methods = ['GET','POST'])
class BootParsing(Resource):
    def get(self, project_name: str):
        #test connexion
        reply = requests.get("https://arboratorgrew.lisn.upsaclay.fr/testBoot/")
        # reply = requests.get("http://127.0.0.1:8001/testBoot/")
        return reply.text

    def post(self,  project_name: str):
        param = request.get_json(force=True)
        #extract names of samples for training set and to parse  
        train_samp_names = param["samples"]
        grew_samples = GrewService.get_samples(project_name)
        all_sample_names = [grew_sample["name"] for grew_sample in grew_samples]

        default_to_parse = all_sample_names if param['to_parse'] == 'ALL' else param['to_parse']

        #get samples 
        train_name, train_set = GrewService.get_samples_with_string_contents(project_name, train_samp_names)
        train_set = [sample.get("last", "") for sample in train_set]
        #TODO assure parse_name not empty
        parse_name, to_parse = GrewService.get_samples_with_string_contents(project_name, default_to_parse) 
        to_parse = [sample.get("last", "") for sample in to_parse]

        # return to_parse
        data = {
            'project_name': project_name,
            'train_name': train_name, 
            'train_set': train_set, 
            'parse_name': parse_name,
            'to_parse': to_parse, 
            'dev': param['dev'],
            'epochs': param['epoch'],
            'parser': param['parser']
            }

        # reply = requests.post("http://127.0.0.1:8001/conllus/", json = data)
        reply = requests.post("https://arboratorgrew.lisn.upsaclay.fr/conllus/", json = data)
        print("########!!",reply.text)

        # return reply.text
        try:
            reply = json.loads(reply.text)
            
        except:
            return {"datasetStatus" : "Failed"}

        return reply


@api.route("/<string:project_name>/samples/parsing/results", methods = ['POST'])
class BootParsedResults(Resource):
    def post(self,  project_name: str):
        param = request.get_json(force=True)
        print(param)
        
        reply = requests.post("https://arboratorgrew.lisn.upsaclay.fr/getResults/", data = {'projectFdname': param['fdname'], 'parser': param['parser']})
        # return reply.text
        try:
            reply = json.loads(reply.text)
        except:
            print(reply.text)
            return {"status" : "Error"}

        status = reply.get('status', None)
        if 'error' in status.lower():
            return {"status" : "Error"}

        if status.lower() == 'fin':
            filenames = reply.get('parsed_names', '')
            files = reply.get('parsed_files', '')
            print(len(filenames))

            for fname, fcontent in zip(filenames, files):
                path_file = os.path.join(Config.UPLOAD_FOLDER, fname)
                print('upload parsed\n', path_file)
                with open(path_file,'w') as f:
                    f.write(fcontent)

                add_or_keep_timestamps(path_file)

                with open(path_file, "rb") as file_to_save:
                    print('save files')
                    GrewService.save_sample(project_name, fname, file_to_save)
        return reply


@api.route("/<string:project_name>/samples/parsing/removeFolder", methods = ['POST', 'PUT'])
class BootParsedRemoveFolder(Resource):
    def post(self,  project_name: str):
        param = request.get_json(force=True)
        print(param)
        
        reply = requests.post("https://arboratorgrew.lisn.upsaclay.fr/removeFolder/", data = {'projectFdname': param['fdname']})
        # return reply.text
        try:
            reply = json.loads(reply.text)
        except:
            print(reply.text)
            return {"status" : "Error"}
        return reply




