from app.projects.service import ProjectAccessService, ProjectService
from app.samples.service import SampleExerciseLevelService
from app.utils.grew_utils import grew_request
from flask import abort, current_app
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

api = Namespace(
    "Trees", description="Endpoints for dealing with trees of a sample"
)  # noqa


@api.route("/<string:projectName>/samples/<string:sampleName>/trees")
class SampleTreesResource(Resource):
    "Trees"

    def get(self, projectName: str, sampleName: str):
        """Entrypoint for getting all trees of a given sample"""
        reply = grew_request(
            "getConll",
            current_app,
            data={"project_id": projectName, "sample_id": sampleName},
        )
        data = reply.get("data")
        if reply.get("status") != "OK":
            abort(409)

        project = ProjectService.get_by_name(projectName)
        if not project:
            abort(404)

        samples = reply.get("data", {})
        ProjectAccessService.require_access_level(project.id, 2)
        ##### exercise mode block #####
        exercise_mode = project.exercise_mode
        project_access: int = 0
        exercise_level: int = 4

        if current_user.is_authenticated:
            project_access = ProjectAccessService.get_by_user_id(
                current_user.id, project.id
            ).access_level.code

        if exercise_mode:
            exercise_level_obj = SampleExerciseLevelService.get_by_sample_name(
                project.id, sampleName
            )
            if exercise_level_obj:
                exercise_level = exercise_level_obj.exercise_level.code

            if project_access == 2:  # isAdmin (= isTeacher)
                sample_trees = samples2trees(samples, sampleName)
            elif project_access == 1:  # isGuest (= isStudent)
                sample_trees = samples2trees_exercise_mode(
                    samples, sampleName, current_user, projectName)
            else:
                abort(409)  # is not authentificated

        ##### end block exercise mode #####

        else:
            if project.show_all_trees or project.visibility == 2:
                sample_trees = samples2trees(samples, sampleName)
            else:
                validator = 1
                # validator = project_service.is_validator(
                #     project.id, sampleName, current_user.id)
                if validator:
                    sample_trees = samples2trees(
                        samples, sampleName)
                else:
                    sample_trees = samples2trees_with_restrictions(
                        samples, sampleName, current_user)

        data = {
            "sample_trees": sample_trees,
            "exercise_level":  exercise_level
        }
        return data

    def post(self, projectName: str, sampleName: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="sent_id", type=str)
        parser.add_argument(name="conll", type=str)
        parser.add_argument(name="user_id", type=str)
        args = parser.parse_args()

        project = ProjectService.get_by_name(projectName)
        project_name = projectName
        sample_name = sampleName
        user_id = args.user_id
        conll = args.conll
        sent_id = args.sent_id

        print("KK saving", sample_name, sent_id)

        if not conll:
            abort(400)
        
        # TODO : add the is_annotator service
        # if project.visibility != 2:
        #     if not project_service.is_annotator(project.id, sample_name, current_user.id) or not project_service.is_validator(project.id, sample_name, current_user.id):
        #         if project.exercise_mode == 0:
        #             abort(403)

        TEACHER = "teacher"
        if (project.exercise_mode == 1 and user_id == TEACHER):
            conll = changeMetaField(conll, "user_id", TEACHER)
        print(">>>>", project_name)
        data={'project_id': project_name, 'sample_id': sample_name,
                    'user_id': user_id, 'sent_id': sent_id, "conll_graph": conll}
        reply = grew_request(
            'saveGraph', current_app,
            data=data
        )
        resp = reply
        print("KK resp", resp)
        if resp["status"] != "OK":
            if "data" in resp:
                response =  {'status': 400, 'message': str(resp["data"])}
            else:
                response = {'status': 400, 'message': 'You idiots!...'}
            response.status_code = 400
            abort(response)

        return {"status":"success"}



################################################################################
##################                                       #######################
##################            Tree functions             #######################
##################                                       #######################
################################################################################
from app.utils.conll3 import changeMetaField, conll2tree, emptyConllu


def samples2trees(samples, sample_name):
    """ transforms a list of samples into a trees object """
    trees = {}
    for sentId, users in samples.items():
        for user_id, conll in users.items():
            tree = conll2tree(conll)
            if sentId not in trees:
                trees[sentId] = {
                    "sample_name": sample_name,
                    "sentence": tree.sentence(),
                    "conlls": {},
                    "matches": {},
                }
            trees[sentId]["conlls"][user_id] = conll
    return trees


def samples2trees_with_restrictions(samples, sample_name, current_user):
    """ transforms a list of samples into a trees object and restrict it to user trees and default tree(s) """
    trees = {}
    # p = project_dao.find_by_name(project_name)
    # default_user_trees_ids = [dut.username for dut in project_dao.find_default_user_trees(p.id)]
    default_user_trees_ids = []
    default_usernames = list()
    default_usernames = default_user_trees_ids
    # if len(default_user_trees_ids) > 0: default_usernames = user_dao.find_username_by_ids(default_user_trees_ids)
    if current_user.username not in default_usernames:
        default_usernames.append(current_user.username)
    for sentId, users in samples.items():
        filtered_users = {
            username: users[username]
            for username in default_usernames
            if username in users
        }
        for user_id, conll in filtered_users.items():
            tree = conll2tree(conll)
            if sentId not in trees:
                trees[sentId] = {
                    "sample_name": sample_name,
                    "sentence": tree.sentence(),
                    "conlls": {},
                    "matches": {},
                }
            trees[sentId]["conlls"][user_id] = conll
    return trees


BASE_TREE = "base_tree"


def samples2trees_exercise_mode(trees_on_grew, sample_name, current_user, project_name):
    """ transforms a list of samples into a trees object and restrict it to user trees and default tree(s) """
    trees_processed = {}
    usernames = ["teacher", current_user.username]

    for tree_id, tree_users in trees_on_grew.items():
        trees_processed[tree_id] = {
            "sample_name": sample_name,
            "sentence": "",
            "conlls": {},
            "matches": {},
        }
        for username, tree in tree_users.items():
            if username in usernames:
                trees_processed[tree_id]["conlls"][username] = tree
                # add the sentence to the dict
                # TODO : put this script on frontend and not in backend (add a conllu -> sentence in javascript)
                # if tree:
                if trees_processed[tree_id]["sentence"] == "":
                    trees_processed[tree_id]["sentence"] = conll2tree(tree).sentence()

                    ### add the base tree (emptied conllu) ###
                    empty_conllu = emptyConllu(tree)
                    base_conllu = changeMetaField(empty_conllu, "user_id", BASE_TREE)
                    trees_processed[tree_id]["conlls"][BASE_TREE] = base_conllu

        if current_user.username not in trees_processed[tree_id]["conlls"]:
            empty_conllu = emptyConllu(tree)
            user_empty_conllu = changeMetaField(
                empty_conllu, "user_id", current_user.username
            )
            trees_processed[tree_id]["conlls"][
                current_user.username
            ] = user_empty_conllu
    return trees_processed
