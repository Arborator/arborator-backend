import json
import re

from app.projects.service import ProjectService
from app.user.service import UserService
from app.utils.grew_utils import GrewService, grew_request
from flask import Response, abort, current_app, request
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

api = Namespace(
    "Grew", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/try-rule")
class TryRuleResource(Resource):
    def post(self, project_name: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)

        # TODO : to change
        if not request.json:
            abort(400)

        parser = reqparse.RequestParser()
        parser.add_argument(name="pattern", type=str)
        parser.add_argument(name="rewriteCommands", type=str)
        args = parser.parse_args()
        pattern = args.get("pattern")
        rewriteCommands = args.get("rewriteCommands")
        # tryRule(<string> project_id, [<string> sample_id], [<string> user_id], <string> pattern, <string> commands)
        reply = grew_request(
            "tryRule",
            data={
                "project_id": project_name,
                "pattern": pattern,
                "commands": rewriteCommands,
            },
        )

        if reply["status"] != "OK":
            if "message" in reply:
                resp = {
                    "status_code": 444,
                    "status": reply["status"],
                    "message": reply["message"],
                }
                status_code = 444
                return resp
            abort(400)
        trees = {}
        # matches={}
        # reendswithnumbers = re.compile(r"_(\d+)$")
        # {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ..
        for m in reply["data"]:
            if m["user_id"] == "":
                abort(409)
            print("___")
            # for x in m:
            # 	print('mmmm',x)
            trees["sample_id"] = trees.get("sample_id", {})
            trees["sample_id"]["sent_id"] = trees["sample_id"].get(
                "sent_id", {"conlls": {}, "nodes": {}, "edges": {}}
            )
            trees["sample_id"]["sent_id"]["conlls"][m["user_id"]] = m["conll"]
            # trees['sample_id']['sent_id']['matches'][m['user_id']]=[{"edges":{},"nodes":{}}] # TODO: get the nodes and edges from the grew server!
            if "sentence" not in trees["sample_id"]["sent_id"]:
                trees["sample_id"]["sent_id"]["sentence"] = conll2tree(
                    m["conll"]
                ).sentence()
            # print('mmmm',trees['sample_id']['sent_id'])
        return trees


@api.route("/<string:project_name>/search")
class SearchResource(Resource):
    "Search"
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="pattern", type=str)
        args = parser.parse_args()

        pattern = args.get("pattern")
        reply = GrewService.search_pattern_in_graphs(project_name, pattern)
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
        args = parser.parse_args()

        pattern = args.get("pattern")
        reply = GrewService.search_pattern_in_graphs(project_name, pattern)
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
        args = parser.parse_args()
        
        package = args.get("package")
        sample_id = args.get("sampleId", None)
        samples_ids = []
        if (sample_id):
            samples_ids = [sample_id]
        reply = GrewService.try_package(project_name, package, samples_ids, passed_user_ids=[], view_only_one=False)
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

        if not sample_ids:
            abort(400)
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




from app.utils.conll3 import conll2tree


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
        t = conll2tree(conll)
        s = t.sentence()
        trees[sample_name][sent_id] = {
            "sentence": s,
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
