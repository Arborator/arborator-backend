import json
import re
import os 

from flask import Response, abort, current_app, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse
from conllup.conllup import sentenceConllToJson
from conllup.processing import constructTextFromTreeJson

from app.config import Config
from app.projects.service import LastAccessService, ProjectService
from app.github.service import GithubCommitStatusService, GithubRepositoryService
from app.utils.grew_utils import SampleExportService, GrewService, grew_request


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
        data = args.get("data")[0]

        for sample_name in data:
            new_conll = str()
            sample_conll = grew_request(
                "getConll",
                data = {"project_id": project_name, "sample_id": sample_name}
            )
            sample_trees = SampleExportService.servSampleTrees(sample_conll.get("data"))
            for sent_id in sample_trees:
                if sent_id in data[sample_name].keys():
                    sample_trees[sent_id] = data[sample_name][sent_id]
                    if ('validated' in data[sample_name][sent_id]["conlls"].keys() and 
                        GithubRepositoryService.get_by_project_id(project.id)):
                        GithubCommitStatusService.update_changes(project.id, sample_name)
                for user in sample_trees[sent_id]["conlls"]:
                    new_conll += sample_trees[sent_id]["conlls"][user] + "\n\n"
            
            file_name = sample_name + "_modified.conllu"
            path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
            with open(path_file, "w") as file:
                file.write(new_conll)
            with open(path_file, "rb") as file_to_save:
                GrewService.save_sample(project_name, sample_name, file_to_save)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/search")
class SearchResource(Resource):
    "Search"
    def post(self, project_name: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="pattern", type=str)
        parser.add_argument(name="userType", type=str)
        parser.add_argument(name="sampleIds",type=str,action="append")
        parser.add_argument(name="otherUser", type=str)
        args = parser.parse_args()

        pattern = args.get("pattern")
        trees_type = args.get("userType") 
        sample_ids = args.get("sampleIds")
        other_user = args.get("otherUser")
        
        print(other_user)
        user_type = 'all' if trees_type == 'pending' else trees_type
        if not sample_ids: 
            sample_ids = [sample["name"] for sample in GrewService.get_samples(project_name)]

        response = GrewService.search_request_in_graphs(project_name, pattern, user_type, other_user)
        
        if response["status"] != "OK":
            abort(400)

        search_results = post_process_grew_results(response["data"], sample_ids, trees_type)
        return search_results


@api.route("/<string:project_name>/try-package")
class TryPackageResource(Resource):
    "rewrite"
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="query", type=str)
        parser.add_argument(name="sampleIds", type=str, action="append")
        parser.add_argument(name="userType", type=str)
        parser.add_argument(name="otherUser", type=str)
        args = parser.parse_args()
        
        package = args.get("query")
        user_type = args.get("userType")
        other_user = args.get("otherUser")
        sample_ids = args.get("sampleIds", None)
        if not sample_ids: 
            sample_ids = []
            
        reply = GrewService.try_package(project_name, package, sample_ids, user_type, other_user)
        if reply["status"] != "OK":
            abort(400)
        trees = {}
        for m in reply["data"]:
            if m["user_id"] == "":
                abort(409)
            trees = formatTrees_new(m, trees, isPackage=True)
        return trees


@api.route("/<string:project_name>/relation-table")
class RelationTableResource(Resource):
    def post(self, project_name):

        parser = reqparse.RequestParser()
        parser.add_argument(name="sampleIds", type=str, action="append")
        parser.add_argument(name="tableType")

        args = parser.parse_args()

        sample_ids = args.get("sampleIds")
        
        tableType = args.get("tableType")
        if not sample_ids: 
            sample_ids = []
        if tableType=='user':
            user_ids = { "one": [current_user.username] }
        elif tableType=='user_recent':
            user_ids = { "one": [current_user.username, "__last__"] }
        elif tableType=='recent':
            user_ids = { "one": ["__last__"] }
        elif tableType=='validated':
            user_ids = { "one": ["validated"]}
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


def formatTrees_new(m, trees, isPackage: bool = False):
    """
    m is the query result from grew
    list of trees
    returns something like {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ...
    """

    user_id = m["user_id"]
    sample_name = m["sample_id"]
    sent_id = m["sent_id"]
    conll = m["conll"]

    if isPackage == False:
        nodes = m["nodes"]
        edges = m["edges"]
    else:
        modified_nodes = m["modified_nodes"]
        modified_edges = m["modified_edges"]

    if sample_name not in trees:
        trees[sample_name] = {}

    if sent_id not in trees[sample_name]:
        try: 
            sentenceJson = sentenceConllToJson(conll)
        except ValueError as e:
            abort(400, 'The result of your query can not be processed by ArboratorGrew')
            
        sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
        trees[sample_name][sent_id] = {
            "sentence": sentence_text,
            "conlls": {user_id: conll},
            "sent_id": sent_id,
           
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


def post_process_grew_results(search_results, sample_ids, trees_type):
    
    trees = {}
    
    for result in search_results:
        if result["sample_id"] not in sample_ids:
            continue
        trees = formatTrees_new(result, trees)

    search_results = {}
    if trees_type == 'pending':
        for sample_id in sample_ids:
            search_results[sample_id] = {
            sent_id: result for sent_id, result in trees[sample_id].items() if 'validated' not in result["conlls"].keys()
        }
            
    else: 
        search_results = trees
    
    return search_results
    
        
                