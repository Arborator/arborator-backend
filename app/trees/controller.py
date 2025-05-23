import os
from flask import abort, request
from flask_login import current_user
from flask_restx import Namespace, Resource
from conllup.processing import changeMetaFieldInSentenceConllu
from conllup.conllup import sentenceConllToJson, sentenceJsonToConll

from app.config import Config
from app.projects.service import LastAccessService, ProjectAccessService, ProjectService
from app.user.service import UserService
from app.samples.service import SampleBlindAnnotationLevelService
from app.github.service import GithubCommitStatusService, GithubRepositoryService
from app.utils.grew_utils import grew_request, GrewService
from app.utils.ud_validator.validate import validate_ud

from .service import TreeService, TreeSegmentationService, TreeValidationService

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

        blind_annotation_mode = project.blind_annotation_mode
        collaborative_mode = project.collaborative_mode

        project_access = 0
        blind_annotation_level = 4

        if current_user.is_authenticated:
            project_access_obj = ProjectAccessService.get_by_user_id(
                current_user.id, project.id
            )

            if project_access_obj:
                project_access = project_access_obj.access_level
                
        if project.visibility == 0 and project_access == 0 and not current_user.super_admin:
            abort(403, "The project is not visible and you don't have the right privileges")

        # if not collaborative mode only validated trees are visible
        if not collaborative_mode:
            sample_trees = TreeService.samples_to_trees(grew_sample_trees, sample_name)
            sample_trees = TreeService.restrict_trees(sample_trees, [VALIDATED])

        if blind_annotation_mode:
            blind_annotation_level_obj = SampleBlindAnnotationLevelService.get_by_sample_name(
                project.id, sample_name
            )
            if blind_annotation_level_obj:
                blind_annotation_level = blind_annotation_level_obj.blind_annotation_level

            sample_trees = TreeService.samples_to_trees(grew_sample_trees, sample_name)
            sample_trees = TreeService.add_base_tree(sample_trees)

            if current_user.is_authenticated:
                username = current_user.username
                if project_access <= 1 and  not current_user.super_admin:
                    sample_trees = TreeService.add_user_tree(sample_trees, username)   
                    restricted_users = [BASE_TREE, VALIDATED, username]
                    sample_trees = TreeService.restrict_trees(sample_trees, restricted_users)
            else:
                restricted_users = [BASE_TREE, VALIDATED]
                sample_trees = TreeService.restrict_trees(sample_trees, restricted_users)
                
        else:
            sample_trees = TreeService.samples_to_trees(grew_sample_trees, sample_name)
               
        if current_user.is_authenticated:
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "read")
            
        data = { "sample_trees": sample_trees, "sent_ids": list(sample_trees.keys()), "blind_annotation_level": blind_annotation_level }
        return data

    def post(self, project_name: str, sample_name: str):
        """
            Entrypoint to save new tree
        Args:
            project_name (str)
            sample_name (str)
            user_id (str)
            conll (str)
            update_commit (bool): if true we update changes number of the sample
            sent_id (str)
        Returns: 
            { "status": "success", "new_conll": with new changes to update frontend view}
        """
        args = request.get_json()
        user_id = args.get("userId")
        conll = args.get("conll")
        update_commit = args.get("updateCommit")
        sent_id = args.get("sentId")
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        
        if not conll:
            abort(400)
            
        if user_id == VALIDATED:
            sentence_json = sentenceConllToJson(conll)
            sentence_json["metaJson"]["validated_by"] = UserService.get_by_id(current_user.id).username
            conll = sentenceJsonToConll(sentence_json)
            
        if project.blind_annotation_mode == 1 and user_id == VALIDATED:
            conll = changeMetaFieldInSentenceConllu(conll, "user_id", VALIDATED)
        
        new_sent_id = sentenceConllToJson(conll)['metaJson']['sent_id']
        if sent_id != new_sent_id: # in case the sent_id is modified all the sent_ids of the other trees will be changed
            TreeService.update_sentence_trees_with_new_sent_id(project_name, sample_name, sent_id, new_sent_id)
        else: 
            data = {
                "project_id": project_name,
                "sample_id": sample_name,
                "user_id": user_id,
                "conll_graph": conll,
            }
            print('tree saved under name: {} by user_id {}'.format(user_id, current_user.id))
            grew_request("saveGraph", data=data)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        if GithubRepositoryService.get_by_project_id(project.id) and user_id == VALIDATED and update_commit:
            GithubCommitStatusService.update_changes(project.id, sample_name)

        return { "status": "success", "new_conll": conll }
    

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/<string:username>")
class UserTreesResource(Resource):
    
    def delete(self, project_name: str, sample_name: str, username: str):
        """Remove trees of specific user """
        data = {"project_id": project_name,  "sample_id": sample_name, "sent_ids": "[]","user_id": username, }
        grew_request("eraseGraphs", data)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")  
        
@api.route("/<string:project_name>/samples/<string:sample_name>/validate")
class ValidateSampleTrees(Resource):
    
    def post(self, project_name: str, sample_name: str):
        """
            Validate all sample
        Args: 
            project_name (str)
            sample_name (str)
        Returns: 
            { message: {"user_1": {"sent_id": message, ....}}}
        """
        project = ProjectService.get_by_name(project_name)
        trees = GrewService.get_samples_with_string_contents(project_name, [sample_name])[1][0]
        mapped_languages = TreeValidationService.extract_ud_languages()
        user_trees_errors = {}
        if project.config == 'ud':
            for user, tree_conll in trees.items():
                if user != 'last':
                    if project.language in mapped_languages.keys():
                        lang_code = mapped_languages[project.language]
                        validation_results = validate_ud(lang_code, 5, tree_conll)[0]
                    else:
                        validation_results = validate_ud(None, 3, tree_conll)[0]   
                    user_trees_errors[user] = TreeValidationService.parse_validation_results(validation_results)
            
            return { "message": user_trees_errors }
                       
@api.route("/<string:project_name>/tree/validate")
class ValidateTree(Resource):
    
    def post(self, project_name: str):
        """
            Validate a specific tree when saving it 
        Args: 
            conll (str)
        Returns: 
            { "message": "validation message", "passed": True | False }
        """
        args = request.get_json()
        data = args.get("conll")
        data = data + '\n' if data.endswith('\n') else data + '\n\n'

        project = ProjectService.get_by_name(project_name)
        mapped_languages = TreeValidationService.extract_ud_languages()

        if project.config == 'ud':
            if project.language in mapped_languages.keys():
                lang_code = mapped_languages[project.language]
                message, passed = validate_ud(lang_code, 5, data)
            else:
                message, passed = validate_ud(None, 3, data)
            return { "message": message if message != '---\n' else '', "passed": passed }
        else: #for the moment if sud we check only the cycles
            cycle_nodes = TreeService.check_cycle(data)
            if cycle_nodes: 
                error_message = 'Non tree structure, tokens: ' + ', '.join([str(list_nodes) for list_nodes in cycle_nodes]) + ' form a cycle'
                return { "message": error_message, "passed": False }
            else:
                return { "message": '', "passed": True }               
            
                      
@api.route("/<string:project_name>/samples/<string:sample_name>/trees/all")
class SaveAllTreesResource(Resource):
    
    def post(self, project_name: str, sample_name: str):
        """Save all trees of sample

        Args:
            project_name (str)
            sample_name (str)
            conllGraph (str)
        """
        data = request.get_json()
        
        file_name = sample_name + "_save_all.conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        
        with open(path_file, "w") as conll_file:
            conll_file.write(data.get('conllGraph'))
            
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)

        os.remove(path_file)

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/split")
class SplitTreeResource(Resource):

    def post(self, project_name: str, sample_name: str):
        """Save splitted sentences, insert new sentences and erase the last sentences

        Args:
            project_name (str)
            sample_name (str)
            sent_id (str)
            firstSents ({ "user_id1": sentence_json, ....})
            secondSents ({ "user_id1": sentence_json })
        """
        project = ProjectService.get_by_name(project_name)
        data = request.get_json()
        sent_id = data.get("sentId")
        inserted_sentences = []
        inserted_sentences.append(data.get("firstSents"))
        inserted_sentences.append(data.get("secondSents"))
        print(inserted_sentences)
        TreeSegmentationService.insert_new_sentences(project_name, sample_name, sent_id, inserted_sentences)
        GrewService.erase_sentence(project_name, sample_name, sent_id)

        if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.update_changes(project.id, sample_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")

@api.route("/<string:project_name>/samples/<string:sample_name>/trees/merge")

class MergeTreesResource(Resource):
    def post(self, project_name: str, sample_name: str):
        """Save merged sentences, insert new sentence and erase the two merged sentences

        Args:
            project_name (str)
            sample_name (str)
            sent_id (str)
            firstSents ({ "user_id1": sentence_json, ....})
            secondSents ({ "user_id1": sentence_json })
        """
        project = ProjectService.get_by_name(project_name)
        data = request.get_json()
        first_sent_id = data.get("firstSentId")
        second_sent_id = data.get("secondSentId")
        inserted_sentences = []
        inserted_sentences.append(data.get("mergedSentences"))

        TreeSegmentationService.insert_new_sentences(project_name, sample_name, first_sent_id, inserted_sentences)
        GrewService.erase_sentence(project_name, sample_name, first_sent_id)
        GrewService.erase_sentence(project_name, sample_name, second_sent_id)

        if GithubRepositoryService.get_by_project_id(project.id):
                GithubCommitStatusService.update_changes(project.id, sample_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")