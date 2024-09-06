# Some utility functions for grew process
import json
from typing import Dict, List, TypedDict

import requests
from flask import abort
from flask_login import current_user
from app import grew_config
import re
import io
import time
import zipfile

def grew_request(fct_name, data={}, files={}):
    try:
        response = requests.post("%s/%s" % (grew_config.server, fct_name), files=files, data=data)

    except requests.ConnectionError:
        error_message = "<Grew requests handler> : Connection refused"
        print(error_message)
        abort(500, {"message": error_message})
    
    except Exception as e:
        error_message = ("Grew requests handler> : Uncaught exception, please report {}".format(e))
        print(error_message)
        abort(500, {"message": error_message})
        
    response = json.loads(response.text)
    if response.get("status") == "ERROR":
        error_message = response.get("message")
        print("GREW-ERROR : {}".format(error_message) )
        abort(406, "GREW-ERROR : {}".format(error_message)) 
        
    elif response.get("status") == "WARNING":
        warning_message = response.get("message")
        print("Grew-Warning: {}".format(warning_message))
        
    return response


class GrewProjectInterface(TypedDict):
    name: str
    number_samples: int
    number_sentences: int
    number_tokens: int
    number_trees: int


class GrewService:
    @staticmethod
    def get_sample_trees(project_name, sample_name) -> Dict[str, Dict[str, str]]:
        response = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_name},
        )
        grew_sample_trees: Dict[str, Dict[str, str]] = response.get("data", {})
        return grew_sample_trees

    @staticmethod
    def get_projects():
        reply = grew_request("getProjects")
        grew_projects: List[GrewProjectInterface] = reply.get("data", [])
        return grew_projects
    
    @staticmethod
    def get_user_projects(username):
        response = grew_request("getUserProjects", data={ "user_id": username })
        user_grew_projects: List[GrewProjectInterface] = response.get("data")
        return user_grew_projects
    

    @staticmethod
    def create_project(project_id: str):
        grew_request(
            "newProject",
            data={"project_id": project_id},
        )

    @staticmethod
    def delete_project(project_id: str):
        grew_request("eraseProject", data={"project_id": project_id})

    @staticmethod
    def rename_project(project_name: str, new_project_name): 
        grew_request("renameProject", data= {
            "project_id": project_name,
            "new_project_id": new_project_name
        })
    
    @staticmethod
    def get_conll_schema(project_id: str):
        grew_reply = grew_request("getProjectConfig", data={"project_id": project_id})
        
        data = grew_reply.get("data")
        if data:
            conll_schema = {
                # be careful, grew_reply["data"] is a list of object. See why, and add an interface for GREW !!
                "annotationFeatures": data[0],
            }
        else:
            conll_schema = {}

        return conll_schema

    @staticmethod
    def update_project_config(project_id: str, dumped_project_config: str) -> None:
        grew_request(
            "updateProjectConfig",
            data={
                "project_id": project_id,
                "config": dumped_project_config,
            },
        )

    @staticmethod
    def get_samples(project_id : str):
        reply = grew_request(
            "getSamples", data={"project_id": project_id}
        )
        grew_samples = reply.get("data", [])

        return grew_samples
    
    @staticmethod
    def create_samples(project_id: str, sample_ids: List[str]):
        reply = grew_request(
            "newSamples",
            data={"project_id": project_id, "sample_ids": json.dumps(sample_ids)},
        )

        return reply

    @staticmethod
    def save_sample(project_id: str, sample_id: str, conll_file) -> None:
        grew_request(
            "saveConll",
            data={"project_id": project_id, "sample_id": sample_id},
            files={"conll_file": conll_file},
        )

    @staticmethod
    def delete_samples(project_id: str, sample_ids: List[str]) -> None:
        grew_request(
            "eraseSamples",
            data={"project_id": project_id, "sample_ids": json.dumps(sample_ids)},
        )

    @staticmethod
    def search_request_in_graphs(project_id: str, request: str, user_type: str, other_user: str):
        
        user_ids = GrewService.get_user_ids(user_type, other_user)
        data = {
            "project_id": project_id,
            "request": request,
            "user_ids": json.dumps(user_ids)
        }
        reply = grew_request("searchRequestInGraphs", data=data)
        return reply

    @staticmethod
    def try_package(project_id: str, package: str, sample_ids, user_type, other_user):
        
        user_ids = GrewService.get_user_ids(user_type, other_user)
        data = {
            "project_id": project_id,
            "package": package,
            "user_ids": json.dumps(user_ids),
            "sample_ids": json.dumps(sample_ids)
        }
        reply = grew_request("tryPackage", data=data)
        return reply
    
    @staticmethod
    def get_relation_table(project_id: str, sample_ids, user_type, other_user):
        
        if not sample_ids: 
            sample_ids = []
        user_ids = GrewService.get_user_ids(user_type, other_user)
        reply = grew_request("relationTables",
            data={
                "project_id": project_id,
                "sample_ids": json.dumps(sample_ids),
                "user_ids": json.dumps(user_ids),
            },
        )
        return reply 
    
    @staticmethod
    def get_lexicon(project_name: str, sample_ids, user_type, other_user, prune, features):
        
        user_ids = GrewService.get_user_ids(user_type, other_user)
        prune = (None, prune) [prune != 0]
        reply = grew_request(
            "getLexicon",
            data={
                "project_id": project_name, 
                "sample_ids": json.dumps(sample_ids), 
                "user_ids": json.dumps(user_ids), 
                "features": json.dumps(features),
                "prune":prune
            },
        )
        return reply
        
    @staticmethod
    def get_user_ids(user_type: str, other_user: str):
        if user_type == 'user':
            user_ids = { "one": [current_user.username] }
        elif user_type == 'user_recent':
            user_ids = { "one": [current_user.username, "__last__"] }
        elif user_type == 'recent':
            user_ids = { "one": ["__last__"] }
        elif user_type == 'validated':
            user_ids = { "one": ["validated"] }
        elif user_type == 'base_tree': 
            user_ids = { "one": ["base_tree"]}
        elif user_type == 'others': 
            user_ids = { "one": [other_user] }
        elif user_type == 'all':
            user_ids = "all"
        return user_ids
        
    @staticmethod
    def insert_conll(project_id: str, sample_id: str, pivot_sent_id: str, conll_file):
        data = {
            "project_id": project_id,
            "sample_id": sample_id,
            "pivot_sent_id": pivot_sent_id
        }
        files = { "conll_file": conll_file }
        grew_request("insertConll", data=data, files=files)

    @staticmethod
    def erase_sentence(project_id: str, sample_id: str, sent_id: str):
        data = {
            "project_id": project_id,
            "sample_id": sample_id,
            "sent_id": sent_id
        }
        grew_request("eraseSentence", data=data)

    @staticmethod
    def get_samples_with_string_contents(project_name: str, sample_names: List[str]):
        samplecontentfiles = list()
        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":

                # {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
                sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
                sample_tree_nots_noui = SampleExportService.serve_sample_trees(reply.get("data", {}), timestamps=False, user_ids=False)
                sample_content = SampleExportService.sample_tree_to_content_file(sample_tree_nots_noui)
                for sent_id in sample_tree:
                    last = SampleExportService.get_last_user(
                        sample_tree[sent_id]["conlls"]
                    )
                    sample_content["last"] = sample_content.get("last", []) + [
                        sample_tree_nots_noui[sent_id]["conlls"][last]
                    ]

                # gluing back the trees
                sample_content["last"] = "".join(sample_content.get("last", ""))
                samplecontentfiles.append(sample_content)

            else:
                print("Error: {}".format(reply.get("message")))
        return sample_names, samplecontentfiles
    
    @staticmethod
    def get_samples_with_string_contents_as_dict(project_name: str, sample_names: List[str], user: str) -> Dict[str, str]:
        samples_dict_for_user: Dict[str, str] = {}
        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":

                # {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
                sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
                sample_tree_nots_noui = SampleExportService.serve_sample_trees(reply.get("data", {}), timestamps=False, user_ids=False)
                sample_content = SampleExportService.sample_tree_to_content_file(sample_tree_nots_noui)
                for sent_id in sample_tree:
                    last = SampleExportService.get_last_user(
                        sample_tree[sent_id]["conlls"]
                    )
                    sample_content["last"] = sample_content.get("last", []) + [
                        sample_tree_nots_noui[sent_id]["conlls"][last]
                    ]

                # gluing back the trees
                sample_content["last"] = "".join(sample_content.get("last", ""))
                samples_dict_for_user[sample_name] =sample_content.get(user, "")

            else:
                print("Error: {}".format(reply.get("message")))
        return samples_dict_for_user
    
    @staticmethod
    def get_validated_trees_filled_up_with_owner_trees(project_name: str, sample_name: str, username: str):
        reply = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_name},
        )
        validated_trees = ""
        if reply.get("status") == "OK":
            sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
            sample_tree_nots_noui = SampleExportService.serve_sample_trees(reply.get("data", {}), timestamps=False, user_ids=False)
            for sent_id in sample_tree:
                if "validated" in sample_tree[sent_id]["conlls"].keys():
                    validated_trees += "".join(sample_tree_nots_noui[sent_id]["conlls"]["validated"])
                else:
                    validated_trees += "".join(sample_tree_nots_noui[sent_id]["conlls"][username])

        return validated_trees

def get_timestamp(conll):
    t = re.search(r"# timestamp = (\d+(?:\.\d+)?)\n", conll)
    if t and t.groups(): 
        return t.groups()[0]
    else:
        return False


class SampleExportService:
    @staticmethod
    def serve_sample_trees(samples, timestamps=True, user_ids=True):
        """ get samples in form of json trees """
        trees = {}
        for sent_id, users in samples.items():
            for user_id, conll in users.items():
                conll+="\n"
                if sent_id not in trees:
                    trees[sent_id] = {"conlls": {}}
                
                # Adapt user_id or timestamps lines depending on options
                if not user_ids: conll = re.sub("# user_id = .+\n", '', conll)
                if not timestamps: conll = re.sub("# timestamp = .+\n", '', conll)

                trees[sent_id]["conlls"][user_id] = conll
        return trees

    @staticmethod
    def sample_tree_to_content_file(tree) -> Dict[str, str]:
        if isinstance(tree, str):
            tree = json.loads(tree)
        usertrees: Dict[str, List[str]] = {}
        for sent_id in tree.keys():
            for user, conll in tree[sent_id]["conlls"].items():
                if user not in usertrees:
                    usertrees[user] = list()
                usertrees[user].append(conll)
        
        to_return_obj = {}
        for user, content in usertrees.items():
            to_return_obj[user] = "".join(content)
        return to_return_obj

    @staticmethod
    def get_last_user(tree):
        timestamps = [(user, get_timestamp(conll)) for (user, conll) in tree.items()]
        if len(timestamps) == 1:
            last = timestamps[0][0]
        else:
            last = sorted(timestamps, key=lambda x: x[1])[-1][0]
        return last

    @staticmethod
    def content_files_to_zip(sample_names, sampletrees, users):
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w") as zf:
            for user in users:
                for sample_name, sample in zip(sample_names, sampletrees):
                    if user in sample.keys():
                        data = zipfile.ZipInfo()
                        data.filename = "{}/{}.conllu".format(user, sample_name) 
                        data.date_time = time.localtime(time.time())[:6]
                        data.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(data, sample.get(user))
        memory_file.seek(0)
        return memory_file