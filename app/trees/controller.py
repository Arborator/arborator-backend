import os
from flask import abort, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from conllup.processing import changeMetaFieldInSentenceConllu

from app.projects.service import LastAccessService, ProjectAccessService, ProjectService
from app.samples.service import SampleBlindAnnotationLevelService
from app.github.service import GithubCommitStatusService, GithubRepositoryService
from app.utils.grew_utils import grew_request, GrewService
from .service import TreeService, TreeSegmentationService

BASE_TREE = "base_tree"
VALIDATED = "validated"

api = Namespace(
    "Trees", description="Endpoints for dealing with trees of a sample"
)  # noqa


@api.route("/<string:project_name>/samples/<string:sample_name>/trees")
class SampleTreesResource(Resource):
    "Trees"

    def get(self, project_name: str, sample_name: str):
        """Entrypoint for getting all trees of a given sample"""
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectService.check_if_freezed(project)

        grew_sample_trees = GrewService.get_sample_trees(project_name, sample_name)

        # ProjectAccessService.require_access_level(project.id, 2)
        ##### exercise mode block #####
        blind_annotation_mode = project.blind_annotation_mode
        project_access = 0
        blind_annotation_level = 4

        if current_user.is_authenticated:
            project_access_obj = ProjectAccessService.get_by_user_id(
                current_user.id, project.id
            )

            if project_access_obj:
                project_access = project_access_obj.access_level.code

        if project.visibility == 0 and project_access == 0:
            abort(403, "The project is not visible and you don't have the right privileges")

        if blind_annotation_mode:
            blind_annotation_level_obj = SampleBlindAnnotationLevelService.get_by_sample_name(
                project.id, sample_name
            )
            if blind_annotation_level_obj:
                blind_annotation_level = blind_annotation_level_obj.blind_annotation_level.code

            sample_trees = TreeService.extract_trees_from_sample(grew_sample_trees, sample_name)
            sample_trees = TreeService.add_base_tree(sample_trees)

            username = "anonymous"
            if current_user.is_authenticated:
                username = current_user.username
                if project_access <= 1:
                    sample_trees = TreeService.add_user_tree(sample_trees, username)

            if project_access <= 1:
                restricted_users = [BASE_TREE, VALIDATED, username]
                sample_trees = TreeService.restrict_trees(sample_trees, restricted_users)
                
        else:
            sample_trees = TreeService.samples2trees(grew_sample_trees, sample_name)
               
        if current_user.is_authenticated:
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "read")
        data = {
            "sample_trees": sample_trees, 
            "sent_ids": list(sample_trees.keys()), 
            "blind_annotation_level": blind_annotation_level
        }
        return data

    def post(self, project_name: str, sample_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="sent_id", type=str)
        parser.add_argument(name="user_id", type=str)
        parser.add_argument(name="conll", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        user_id = args.user_id
        conll = args.conll
        sent_id = args.sent_id
        if not conll:
            abort(400)


        if project.blind_annotation_mode == 1 and user_id == VALIDATED:
            conll = changeMetaFieldInSentenceConllu(conll, "user_id", VALIDATED)
        data = {
            "project_id": project_name,
            "sample_id": sample_name,
            "user_id": user_id,
            "conll_graph": conll,
        }

        grew_request("saveGraph", data=data)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        if GithubRepositoryService.get_by_project_id(project.id) and user_id == VALIDATED:
            GithubCommitStatusService.update_changes(project.id, sample_name)

        return {"status": "success"}
    

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/<string:username>")
class UserTreesResource(Resource):
    
    def delete(self, project_name: str, sample_name: str, username: str):
        data = {"project_id": project_name,  "sample_id": sample_name, "sent_ids": "[]","user_id": username, }
        grew_request("eraseGraphs", data)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")  


@api.route("/<string:project_name>/samples/<string:sample_name>/trees/split")
class SplitTreeResource(Resource):

    def post(self, project_name: str, sample_name: str):
        
        project = ProjectService.get_by_name(project_name)
        data = request.get_json()
        sent_id = data.get("sentId")
        inserted_sentences = []
        inserted_sentences.append(data.get("firstSents"))
        inserted_sentences.append(data.get("secondSents"))

        TreeSegmentationService.insert_new_sentences(project_name, sample_name, sent_id, inserted_sentences)
        GrewService.eraseSentence(project_name, sample_name, sent_id)

        if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.update_changes(project.id, sample_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/merge")

class MergeTreesResource(Resource):
    def post(self, project_name: str, sample_name: str):

        project = ProjectService.get_by_name(project_name)
        data = request.get_json()
        first_sent_id = data.get("firstSentId")
        second_sent_id = data.get("secondSentId")
        inserted_sentences = []
        inserted_sentences.append(data.get("mergedSentences"))

        TreeSegmentationService.insert_new_sentences(project_name, sample_name, first_sent_id, inserted_sentences)
        GrewService.eraseSentence(project_name, sample_name, first_sent_id)
        GrewService.eraseSentence(project_name, sample_name, second_sent_id)

        if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.update_changes(project.id, sample_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
