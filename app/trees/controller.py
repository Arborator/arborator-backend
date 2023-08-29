from flask import abort
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from conllup.conllup import sentenceConllToJson
from conllup.processing import constructTextFromTreeJson, emptySentenceConllu, changeMetaFieldInSentenceConllu

from app.projects.service import LastAccessService, ProjectAccessService, ProjectService
from app.samples.service import SampleBlindAnnotationLevelService
from app.github.service import GithubCommitStatusService, GithubSynchronizationService
from app.utils.grew_utils import grew_request, GrewService
from .service import TreeService

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
        project_access: int = 0
        blind_annotation_level: int = 4
        if current_user.is_authenticated:
            project_access_obj = ProjectAccessService.get_by_user_id(
                current_user.id, project.id
            )

            if project_access_obj:
                project_access = project_access_obj.access_level.code

        if project.visibility == 0 and project_access == 0:
            abort(
                403,
                "The project is not visible and you don't have the right privileges",
            )

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
            if  project.visibility == 2:
                sample_trees = TreeService.samples2trees(grew_sample_trees, sample_name)
            else:
                validator = 1
                if validator:
                    sample_trees = TreeService.samples2trees(
                        grew_sample_trees,
                        sample_name,
                    )
                else:
                    sample_trees = TreeService.samples2trees_with_restrictions(
                        grew_sample_trees,
                        sample_name,
                        current_user,
                    )
        if current_user.is_authenticated:
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "read")
        data = {"sample_trees": sample_trees, "blind_annotation_level": blind_annotation_level}
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
        if GithubSynchronizationService.get_github_synchronized_repository(project.id):
            GithubCommitStatusService.update(project_name, sample_name)

        return {"status": "success"}
    

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/<string:username>")
class UserTreesResource(Resource):
    
    def delete(self, project_name: str, sample_name: str, username: str):
        data = {"project_id": project_name,  "sample_id": sample_name, "sent_ids": "[]","user_id": username, }
        grew_request("eraseGraphs", data)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")  





