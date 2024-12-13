import json
import re
from typing import List

from flask.helpers import send_file
from flask_accepts.decorators.decorators import responds
from flask import Response, request
from flask_restx import Namespace, Resource 
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.projects.service import ProjectAccessService, ProjectService, LastAccessService
from app.utils.grew_utils import GrewService, SampleExportService, grew_request
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
        """Get list of samples of project

        Args:
            project_name (str)

        Returns:
            List[SampleSchema]
        """
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
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
                "tags": grew_sample["tags"]
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
        
        """Upload new samples

        Args: 
            - project_name(str)
            - user_id(str): username used to the uploaded trees
            - files(List[File])
            - rtl(bool): right to lef script
            - samples_without_sent_ids(List[str])

        Returns:
            - { "status": ok, "response": list of detected annotation tag in the uploaded samples}
        """
        
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
            sample_names = []
            
            for file in files:
                
                filename = secure_filename(file.filename)
                sample_name = reextensions.sub("", filename)
                sample_names.append(sample_name)
                
                SampleUploadService.upload(
                    file,
                    project_name,
                    filename, 
                    sample_name,
                    rtl,
                    existing_samples=existing_samples,
                    new_username=username,
                    samples_without_sent_ids=samples_without_sent_ids
                )
            
            pos_list, relation_list, feat_list, misc_list = GrewService.get_config_from_samples(project_name, sample_names)
            
            response = {
                "pos": pos_list,
                "relations": relation_list,
                "feats": feat_list,
                "misc": misc_list
            }
            
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
            
            return { "status": "OK", "data": response }
        
    def patch(self, project_name: str):
        """
            Delete samples in the project instead of using delete method and 
            since we can delete a batch of samples so we are using patch

        Args:
            project_name (str)
        """

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

@api.route("/<string:project_name>/samples/<string:sample_name>/sample-name")
class SampleNameResource(Resource):
    
    def post(self, project_name, sample_name):
        
        """Rename an existing sample
        Args:
            - project_name(str)
            - sample_name(str)
            - newSampleName(str)
        """
        args = request.get_json()
        new_sample_name = args.get("newSampleName")
        
        response = grew_request("renameSample", {
            "project_id": project_name,
            "sample_id": sample_name,
            "new_sample_id": new_sample_name
        })
        
        return response
                      
@api.route("/<string:project_name>/samples/tokenize")
class SampleTokenizeResource(Resource):
    def post(self, project_name):
        """Create new sample using tokenizer

        Args:
            project_name (str)
            username: the username used for the uploaded trees
            option(str): horizontal, vertical or plain text
            lang(str): for plain text there is two languages (french or english)
            text(str)
            rtl(bool): right to left script
        """
        args = request.get_json()
        username = args.get("username")
        sample_name = args.get("sampleName")
        option = args.get("option")
        lang = args.get("lang")
        text = args.get("text")
        rtl = args.get("rtl")
        
        SampleTokenizeService.tokenize(text, option, lang, project_name, sample_name, username, rtl)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/samples/<string:sample_name>/blind-annotation-level")
class SampleBlindAnnotationLevelResource(Resource):
    
    def post(self, project_name: str, sample_name: str):
        """update blind annotation level of a sample

        Args:
            project_name (str)
            sample_name (str)
            blind_annotation_level(int)
        """
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
        """
            Export evaluation of students in blind annotation mode in a tsv file 
        Args:
            project_name (str)
            sample_name (str)

        Returns:
            file send as an attachement
        """
        sample_conlls = GrewService.get_sample_trees(project_name, sample_name)
        evaluations = SampleEvaluationService.evaluate_sample(sample_conlls)
        evaluations_tsv = SampleEvaluationService.evaluations_json_to_tsv(evaluations)
        uploadable_evaluations_tsv = SharedService.get_sendable_data(evaluations_tsv)
        file_name = f"{sample_name}_evaluations.tsv"
        return send_file(uploadable_evaluations_tsv, download_name=file_name, as_attachment=True)


@api.route("/<string:project_name>/samples/export")
class ExportSampleResource(Resource):
    
    def post(self, project_name: str):
        """Export trees from samples

        Args:
            project_name (str)
            sample_names (List[str])
            users (List[str]): the trees of user that will be exported
        Returns:
            zip file as an attachement
        """
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

