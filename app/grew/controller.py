import json
import re

from app.projects.service import LastAccessService, ProjectService
from app.user.service import UserService
from app.github.service import GithubCommitStatusService, GithubSynchronizationService
from app.utils.grew_utils import GrewService, grew_request
from flask import Response, abort, current_app, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from conllup.conllup import sentenceConllToJson
from conllup.processing import constructTextFromTreeJson


api = Namespace(
    "Grew", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/apply-rule")
class ApplyRuleResource(Resource):
    def post(self, project_name: str):

        project =ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        parser = reqparse.RequestParser()
        parser.add_argument(name="data", type=dict, action="append")
        args = parser.parse_args()
        data = args.get("data")

        for index in range(len(data)):
            for sample_name, search_results in data[index].items():
                for sent_id, sentence in search_results.items(): 
                    grew_request("saveGraph",
                    data={
                        "project_id": project_name,
                        "sample_id": sample_name,
                        "user_id": list(sentence['conlls'].keys())[0],
                        "conll_graph": list(sentence['conlls'].values())[0],
                    })
                    if GithubSynchronizationService.get_github_synchronized_repository(project.id):
                        GithubCommitStatusService.update(project_name, sample_name)

        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return {"status": "success"}


@api.route("/<string:project_name>/search")
class SearchResource(Resource):
    "Search"
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="pattern", type=str)
        parser.add_argument(name="userType", type=str)
        args = parser.parse_args()

        pattern = args.get("pattern")
        user_type = args.get("userType") 
        

        reply = GrewService.search_pattern_in_graphs(project_name, pattern, user_type)
        if reply["status"] != "OK":
            abort(400)
        trees = {}
        for m in reply["data"]:
            if m["user_id"] == "":
                abort(409)
            conll = m["conll"]
            trees = formatTrees_new(m, trees, conll)
        return trees


@api.route("/<string:project_name>/sample/<string:sample_name>/search")
class SearchInSampleResource(Resource):
    def post(self, project_name: str, sample_name: str):
        """
        Aplly a grew search inside a project and sample
        """
        reply = grew_request("getSamples", data={"project_id": project_name})
        data = reply.get("data")
        samples_name = [sa["name"] for sa in data]
        if not sample_name in samples_name:
            abort(404)

        parser = reqparse.RequestParser()
        parser.add_argument(name="pattern", type=str)
        parser.add_argument(name="userType", type=str)
        args = parser.parse_args()

        pattern = args.get("pattern")
        user_type = args.get("userType")
        reply = GrewService.search_pattern_in_graphs(project_name, pattern, user_type)
        trees = {}
        for m in reply["data"]:
            if m["sample_id"] != sample_name:
                continue
            if m["user_id"] == "":
                abort(409)
            conll = m["conll"]
            trees = formatTrees_new(m, trees, conll)
        return trees

@api.route("/<string:project_name>/try-package")
class TryPackageResource(Resource):
    "Search"
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="package", type=str)
        parser.add_argument(name="sampleId", type=str)
        parser.add_argument(name="userType", type=str)
        args = parser.parse_args()
        
        package = args.get("package")
        user_type = args.get("userType")
        sample_id = args.get("sampleId", None)
        samples_ids = []
        if (sample_id):
            samples_ids = [sample_id]
        reply = GrewService.try_package(project_name, package, samples_ids, user_type)
        if reply["status"] != "OK":
            abort(400)
        trees = {}
        for m in reply["data"]:
            if m["user_id"] == "":
                abort(409)
            conll = m["conll"]
            trees = formatTrees_new(m, trees, conll, isPackage=True)
        return trees



@api.route("/<string:project_name>/old-relation-table")
class RelationTableResource(Resource):
    def post(self, project_name):
        # TODO : if user is not currently authenticated, they should only have access to recent mode
        # @login_required
        parser = reqparse.RequestParser()
        parser.add_argument(name="table_type", type=str)
        args = parser.parse_args()
        table_type = args.get("table_type")
        if not table_type:
            abort(400)
        reply = grew_request(
            "searchPatternInGraphs",
            data={
                "project_id": project_name,
                "pattern": "pattern { e: GOV -> DEP}",
                "clusters": ["e.label; GOV.upos; DEP.upos"],
                "user_ids": "[]",
            },
        )
        if reply["status"] != "OK":
            abort(400)
        data = reply.get("data")
        for e, v in data.items():
            for gov, vv in v.items():
                for dep, vvv in vv.items():
                    trees = dict()
                    for elt in vvv:
                        if table_type == "user":
                            if elt["user_id"] != current_user.username:
                                continue
                            else:
                                conll = elt.get("conll")
                                trees = formatTrees_new(elt, trees, conll)
                        else:
                            conll = elt.get("conll")
                            trees = formatTrees_new(elt, trees, conll)

                    # filtering out
                    if table_type == "recent":
                        for samp in trees:
                            for sent in trees[samp]:
                                last = get_last_user(trees[samp][sent]["conlls"])
                                trees[samp][sent]["conlls"] = {
                                    last: trees[samp][sent]["conlls"][last]
                                }
                                trees[samp][sent]["matches"] = {
                                    last: trees[samp][sent]["matches"][last]
                                }
                    elif table_type == "user_recent":
                        for samp in trees:
                            for sent in trees[samp]:
                                if current_user.username in trees[samp][sent]["conlls"]:
                                    trees[samp][sent]["conlls"] = {
                                        current_user.username: trees[samp][sent][
                                            "conlls"
                                        ][current_user.username]
                                    }
                                    trees[samp][sent]["matches"] = {
                                        current_user.username: trees[samp][sent][
                                            "matches"
                                        ][current_user.username]
                                    }
                                else:
                                    last = get_last_user(trees[samp][sent]["conlls"])
                                    trees[samp][sent]["conlls"] = {
                                        last: trees[samp][sent]["conlls"][last]
                                    }
                                    trees[samp][sent]["matches"] = {
                                        last: trees[samp][sent]["matches"][last]
                                    }
                    elif table_type == "all":
                        pass
                    data[e][gov][dep] = trees
        return data


@api.route("/<string:project_name>/relation-table")
class RelationTableResource(Resource):
    def post(self, project_name):
        # TODO : if user is not currently authenticated, they should only have access to recent mode
        # @login_required
        parser = reqparse.RequestParser()
        parser.add_argument(name="sample_id")
        parser.add_argument(name="tableType")
        args = parser.parse_args()
        sample_id = args.get("sample_id")
        if sample_id:
            sample_ids = [sample_id]
        else:
            sample_ids = []
        tableType = args.get("tableType")
        if tableType=='user':
            user_ids = { "one": [current_user.username] }
        elif tableType=='user_recent':
            user_ids = { "one": [current_user.username, "__last__"] }
        elif tableType=='recent':
            user_ids = { "one": ["__last__"] }
        elif tableType=='all':
            user_ids = "all"
        reply = grew_request(
            "relationTables",
            data={
                "project_id": project_name,
                "sample_ids": json.dumps(sample_ids),
                "user_ids": json.dumps(user_ids),
            },
        )
        if reply["status"] != "OK":
            abort(400)
        data = reply.get("data")    
        return data


@api.route("/<string:project_name>/show-diff")
class ShowDiffRessource(Resource):
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="otherUsers", type=str, action="append")
        parser.add_argument(name="features", type=str, action="append")
        parser.add_argument(name="sampleName", type=str)
        args = parser.parse_args()

        sample_name = args.get("sampleName")
        other_users = args.get("otherUsers")
        features = args.get("features")
        pattern = "pattern { }"
        user_type = "all"

        reply = GrewService.search_pattern_in_graphs(project_name, pattern, user_type)
        if reply["status"] != "OK":
            abort(400)
        trees = {}
        for m in reply["data"]:
            if sample_name:
                if m["sample_id"] != sample_name:
                    continue
                if m["user_id"] == "":
                    abort(409)
                conll = m["conll"]
                trees = formatTrees_new(m, trees, conll)
            else: 
                if m["user_id"] == "":
                    abort(409)
                conll = m["conll"]
                trees = formatTrees_new(m, trees, conll)
        return post_process_diffs(trees, other_users, features)
        

def get_timestamp(conll):
    t = re.search("# timestamp = (\d+(?:\.\d+)?)\n", conll).groups()
    if t:
        return t[0]
    else:
        return False


def get_last_user(tree):
    timestamps = [(user, get_timestamp(conll)) for (user, conll) in tree.items()]
    if len(timestamps) == 1:
        last = timestamps[0][0]
    else:
        # print(timestamps)
        last = sorted(timestamps, key=lambda x: x[1])[-1][0]
        # print(last)
    return last


def formatTrees_new(m, trees, conll, isPackage: bool = False):
    """
    m is the query result from grew
    list of trees
    returns something like {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ...
    """

    user_id = m["user_id"]
    sample_name = m["sample_id"]
    sent_id = m["sent_id"]

    if isPackage == False:
        nodes = m["nodes"]
        edges = m["edges"]
    else:
        modified_nodes = m["modified_nodes"]
        modified_edges = m["modified_edges"]

    if sample_name not in trees:
        trees[sample_name] = {}

    if sent_id not in trees[sample_name]:
        sentenceJson = sentenceConllToJson(conll)
        sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
        trees[sample_name][sent_id] = {
            "sentence": sentence_text,
            "conlls": {user_id: conll},
           
        }
        if isPackage == False:
            trees[sample_name][sent_id]["matches"] = {user_id: [{"edges": edges, "nodes": nodes}]}
        else:
            trees[sample_name][sent_id]["packages"] = {user_id: {"modified_edges": modified_edges, "modified_nodes": modified_nodes}}
    
    
    else:
        trees[sample_name][sent_id]["conlls"][user_id] = conll
        # /!\ there can be more than a single match for a same sample, sentence, user so it has to be a list
        if isPackage == False:
            trees[sample_name][sent_id]["matches"][user_id] = trees[sample_name][sent_id][
                "matches"
            ].get(user_id, []) + [{"edges": edges, "nodes": nodes}]
        else:
            trees[sample_name][sent_id]["packages"][user_id] = {"modified_edges": modified_edges, "modified_nodes": modified_nodes}

        
    return trees


def check_all_diffs(left_sentence_json, right_sentence_json):

    left_nodes_json = left_sentence_json["treeJson"]["nodesJson"]
    right_nodes_json = right_sentence_json["treeJson"]["nodesJson"]
    if len(left_nodes_json.values()) != len(right_nodes_json.values()):
            return True
    else: 
        for token_id in left_nodes_json:
            left_token = left_nodes_json[token_id]
            right_token = right_nodes_json[token_id]
            if json.dumps(left_token) != json.dumps(right_token):
                return True


def check_diffs_based_on_feats(left_sentence_json, right_sentence_json, features):
    left_nodes_json = left_sentence_json["treeJson"]["nodesJson"]
    right_nodes_json = right_sentence_json["treeJson"]["nodesJson"]
    diff_token_ids =  set()
    if len(left_nodes_json.values()) == len(right_nodes_json.values()):
        for token_id in left_nodes_json:
            left_token = left_nodes_json[token_id]
            right_token = right_nodes_json[token_id]
            if left_token['FORM'] == right_token['FORM']:
                for feat in features:
                    if '.' in feat: 
                        base_feat = feat.split('.')[0]
                        second_feat = feat.split('.')[1]
                        if  second_feat in left_token[base_feat].keys() and second_feat in  right_token[base_feat].keys():
                            if  left_token[base_feat][second_feat]!= right_token[base_feat][second_feat]:
                                diff_token_ids.add(token_id)
                    else:
                        if left_token[feat] != right_token[feat]:
                            diff_token_ids.add(token_id)

        return diff_token_ids


def post_process_diffs(grew_search_results, other_users, features):

    user_id = other_users[0]
    post_processed_results = {}
    for sample_name in grew_search_results:
        post_processed_results[sample_name] = {}
        for sent_id in  grew_search_results[sample_name]:
            if user_id in grew_search_results[sample_name][sent_id]["conlls"].keys():
                user_sentence_json = sentenceConllToJson(grew_search_results[sample_name][sent_id]["conlls"][user_id])
                conlls = {}
                matches = {}
                for other_user_id in other_users[1:]:
                    if (other_user_id in grew_search_results[sample_name][sent_id]["conlls"].keys()):
                        other_sentence_json = sentenceConllToJson(grew_search_results[sample_name][sent_id]["conlls"][other_user_id])
                        if not features:
                            if check_all_diffs(user_sentence_json, other_sentence_json):
                                conlls[other_user_id] = grew_search_results[sample_name][sent_id]["conlls"][other_user_id]
                        else:
                            token_ids = check_diffs_based_on_feats(user_sentence_json, other_sentence_json, features)
                            if token_ids:
                                list_matches = []
                                for token_id in token_ids:
                                    list_matches.append({"edges":'' , "nodes": {"N": token_id} }) 
                            
                                matches[other_user_id] = list_matches
                                conlls[other_user_id] = grew_search_results[sample_name][sent_id]["conlls"][other_user_id]           
                if len(conlls) > 0 : 
                    print('test')
                    post_processed_results[sample_name][sent_id] = {
                        "sentence": grew_search_results[sample_name][sent_id]["sentence"],
                        "sample_name": sample_name,
                        "conlls": conlls,
                        "matches": matches,
                        "packages": {},
                    }

                    post_processed_results[sample_name][sent_id]["conlls"][user_id] = grew_search_results[sample_name][sent_id]["conlls"][user_id]                                    
    return post_processed_results

                