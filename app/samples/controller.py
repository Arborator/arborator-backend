import json
import re
from typing import List

from flask.helpers import send_file
from flask_accepts.decorators.decorators import responds
from flask import Response, request
from flask_restx import Namespace, Resource 
from flask_login import current_user

from app.projects.service import ProjectAccessService, ProjectService, LastAccessService
from app.utils.grew_utils import GrewService, SampleExportService
from app.shared.service import SharedService

from .service import (
    SampleEvaluationService,
    SampleBlindAnnotationLevelService,
    SampleUploadService,
    SampleTokenizeService,
)
from .interface import SampleInterface
from .schema import SampleSchema

api = Namespace(
    "Samples", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/samples")
class SampleResource(Resource):
    "Samples"
    
    @responds(schema=SampleSchema(many=True), api=api)
    def get(self, project_name: str):
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        grew_samples = GrewService.get_samples(project_name)

        processed_samples: List[SampleInterface] = []
        
        for grew_sample in grew_samples:
            sample = {
                "sample_name": grew_sample["name"],
                "sentences": grew_sample["number_sentences"],
                "number_trees": grew_sample["number_trees"],
                "tokens": grew_sample["number_tokens"],
                "trees_from": list(grew_sample["tree_by_user"].keys()),
                "tree_by_user": grew_sample["tree_by_user"],
            }
            blind_annotation_level = SampleBlindAnnotationLevelService.get_by_sample_name(
                project.id, grew_sample["name"]
            )
            if blind_annotation_level:
                sample["blind_annotation_level"] = blind_annotation_level.blind_annotation_level
            else:
                sample["blind_annotation_level"] = 4

            processed_samples.append(sample)
        return processed_samples


    def post(self, project_name: str):
        
        
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        ProjectService.check_if_freezed(project)

        username = request.form.get("userId")   
        files = request.files.to_dict(flat=False).get("files")
        samples_without_sent_ids = request.form.get("samplesWithoutSentIds")
        rtl = request.form.get("rtl")
        
        rtl = json.loads(rtl)
        
        if samples_without_sent_ids:
            samples_without_sent_ids = json.loads(samples_without_sent_ids)

        if files:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")
            grew_samples = GrewService.get_samples(project_name)
            existing_samples = [sa["name"] for sa in grew_samples]

            for file in files:
                SampleUploadService.upload(
                    file,
                    project_name,
                    rtl,
                    reextensions=reextensions,
                    existing_samples=existing_samples,
                    new_username=username,
                    samples_without_sent_ids=samples_without_sent_ids
                )
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
            return {"status": "OK"}
        
    def patch(self, project_name: str):

        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        ProjectService.check_if_freezed(project)
        ProjectService.check_if_project_exist(project)
        
        args = request.get_json(force=True)
        sample_ids = args.get("sampleIds")
        
        GrewService.delete_samples(project_name, sample_ids)
        for sample_id in sample_ids:
            SampleBlindAnnotationLevelService.delete_by_sample_name(project.id, sample_id)

        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return { "status": "OK" }
          
@api.route("/<string:project_name>/samples/tokenize")
class SampleTokenizeResource(Resource):
    def post(self, project_name):
        
        args = request.get_json()
        username = args.get("username")
        sample_name = args.get("sampleName")
        option = args.get("option")
        lang = args.get("lang")
        text = args.get("text")
        rtl = args.get("rtl")
        
        SampleTokenizeService.tokenize(text, option, lang, project_name, sample_name, username)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/samples/<string:sample_name>/blind-annotation-level")
class SampleBlindAnnotationLevelResource(Resource):
    
    def post(self, project_name: str, sample_name: str):
        
        args = request.get_json()
        blind_annotation_level = args.get("blindAnnotationLevel")

        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)

        sample_blind_annotation_level = SampleBlindAnnotationLevelService.get_by_sample_name(
            project.id, sample_name
        )

        new_attrs = {
            "project_id": project.id,
            "sample_name": sample_name,
            "blind_annotation_level": blind_annotation_level,
        }

        if sample_blind_annotation_level:
            SampleBlindAnnotationLevelService.update(sample_blind_annotation_level, new_attrs)
        else:
            SampleBlindAnnotationLevelService.create(new_attrs)

        return {"status": "success"}


@api.route("/<string:project_name>/samples/<string:sample_name>/evaluation")
class SampleEvaluationResource(Resource):
    
    def get(self, project_name, sample_name):
        
        sample_conlls = GrewService.get_sample_trees(project_name, sample_name)
        evaluations = SampleEvaluationService.evaluate_sample(sample_conlls)
        evaluations_tsv = SampleEvaluationService.evaluations_json_to_tsv(evaluations)
        uploadable_evaluations_tsv = SharedService.get_sendable_data(evaluations_tsv)
        file_name = f"{sample_name}_evaluations.tsv"
        return send_file(uploadable_evaluations_tsv, file_name, as_attachment=True)


@api.route("/<string:project_name>/samples/export")
class ExportSampleResource(Resource):
    
    def post(self, project_name: str):
        
        args = request.get_json()
        sample_names = args.get("sampleNames")
        users = args.get("users")
        sample_names, samples_with_string_content = GrewService.get_samples_with_string_contents(project_name, sample_names)

        memory_file = SampleExportService.content_files_to_zip(
            sample_names, samples_with_string_content, users
        )

        resp = Response(
            memory_file,
            status=200,
            mimetype="application/zip",
            headers={
                "Content-Disposition": "attachment;filename=dump.{}.zip".format(project_name)
            },
        )
        return resp

