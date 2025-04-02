import json
from typing import Dict, List, TypedDict
import re
import io
import time
import zipfile
from bs4 import BeautifulSoup

import requests
from flask import abort
from flask_login import current_user
import werkzeug
from app import grew_config
from app.user.service import EmailService

from conllup.conllup import sentenceConllToJson
from conllup.processing import constructTextFromTreeJson


def grew_request(fct_name, data={}, files={}):
    """Send grew request

    Args:
        fct_name (str)
        data (dict, optional)
        files (dict, optional)

    Returns:
        grew_response ({"status": "", "data": ..., "messages": ... })
    """
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
    try: 
        response = json.loads(response.text)
        if response.get("status") == "ERROR":
            error_message = response.get("message")
            print("GREW-ERROR : {}".format(error_message) )
            abort(406, "GREW-ERROR : {}".format(error_message))
            
        elif response.get("status") == "WARNING":
            warning_message = response.get("message")
            print("Grew-Warning: {}".format(warning_message))    
        return response
    
    except Exception as e:
        if isinstance(e, werkzeug.exceptions.NotAcceptable): # to fix the problem of abort inside try-except block
            raise
        parsed_error_msg = BeautifulSoup(response.text, features="lxml").find('p').contents[0]
        EmailService.send_alert_email('Grew server error', str(parsed_error_msg))
        abort(500, str(parsed_error_msg))
        

class GrewProjectInterface(TypedDict):
    name: str
    number_samples: int
    number_sentences: int
    number_tokens: int
    number_trees: int


class GrewService:
    """Class for grew request functions """
    @staticmethod
    def get_sample_trees(project_name, sample_name) -> Dict[str, Dict[str, str]]:
        """Get sample trees

        Args:
            project_name (str)
            sample_name (str)

        Returns:
            Dict[str, Dict[str, str]]
        """
        response = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_name},
        )
        grew_sample_trees: Dict[str, Dict[str, str]] = response.get("data", {})
        return grew_sample_trees

    @staticmethod
    def get_projects():
        """Get list of projects stored in grew server

        Returns:
            grew_projects(List(GrewProjectInterface))
        """
        reply = grew_request("getProjects")
        grew_projects: List[GrewProjectInterface] = reply.get("data", [])
        return grew_projects
    
    @staticmethod
    def get_user_projects(username):
        """Get list of user projects (grew projects where user has saved tree under their name)

        Args:
            username (str)

        Returns:
            user_grew_projects (List[GrewProjectInterface])
        """
        response = grew_request("getUserProjects", data={ "user_id": username })
        user_grew_projects: List[GrewProjectInterface] = response.get("data")
        return user_grew_projects
    

    @staticmethod
    def create_project(project_id: str):
        """create new project in grew server

        Args:
            project_id (str)
        """
        grew_request(
            "newProject",
            data={"project_id": project_id},
        )

    @staticmethod
    def delete_project(project_id: str):
        """Delete project from grew server

        Args:
            project_id (str)
        """
        grew_request("eraseProject", data={"project_id": project_id})

    @staticmethod
    def rename_project(project_name: str, new_project_name: str): 
        """Rename existing project

        Args:
            project_name (str)
            new_project_name (str)
        """
        grew_request("renameProject", data= {
            "project_id": project_name,
            "new_project_id": new_project_name
        })
    
    @staticmethod
    def get_conll_schema(project_id: str):
        """Get conll config schema from grew server

        Args:
            project_id (str)

        Returns:
            conll_schema ({"annotationFeatures":  json dict})
        """
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
    def update_project_config(project_id, dumped_project_config) -> None:
        """update project schema

        Args:
            project_id (str)
            dumped_project_config (dict)
        """
        grew_request(
            "updateProjectConfig",
            data={
                "project_id": project_id,
                "config": json.dumps(dumped_project_config),
            },
        )

    @staticmethod
    def get_samples(project_id : str):
        """Get samples from grew server

        Args:
            project_id (str)

        Returns:
            grew_samples (List[grew_sample])
        """
        reply = grew_request(
            "getSamples", data={"project_id": project_id}
        )
        grew_samples = reply.get("data", [])

        return grew_samples
    
    @staticmethod
    def create_samples(project_id: str, sample_ids: List[str]):
        """Create samples

        Args:
            project_id (str)
            sample_ids (List[str]): sample_ids can also contain only one sample_name
        """
        reply = grew_request(
            "newSamples",
            data={"project_id": project_id, "sample_ids": json.dumps(sample_ids)},
        )

        return reply

    @staticmethod
    def save_sample(project_id: str, sample_id: str, conll_file) -> None:
        """Save sample content in grew

        Args:
            project_id (str)
            sample_id (str)
            conll_file (File)
        """
        grew_request(
            "saveConll",
            data={"project_id": project_id, "sample_id": sample_id},
            files={"conll_file": conll_file},
        )

    @staticmethod
    def delete_samples(project_id: str, sample_ids: List[str]) -> None:
        """delete sample of specific project

        Args:
            project_id (str)
            sample_ids (List[str])
        """
        grew_request(
            "eraseSamples",
            data={"project_id": project_id, "sample_ids": json.dumps(sample_ids)},
        )

    @staticmethod
    def search_request_in_graphs(project_id: str, request: str, sample_ids: List[str], user_type: str, other_user: str):
        """Grew search

        Args:
            project_id (str)
            request (str)
            sample_ids (List[str])
            user_type (str)
            other_user (str)

        Returns:
            grew_search results ("sent_id": {
                'sample_id':…,
                'sent_id':…,
                'conll':…,
                'user_id':…,
                'nodes':…,
                'edges':…
            })
        """
        user_ids = GrewService.get_user_ids(user_type, other_user)
        data = {
            "project_id": project_id,
            "request": request,
            "user_ids": json.dumps(user_ids),
            "sample_ids": json.dumps(sample_ids)
        }
        reply = grew_request("searchRequestInGraphs", data=data)
        return reply

    @staticmethod
    def try_package(project_id: str, package: str, sample_ids: List[str], user_type: str, other_user: str):
        """Search rewrite

        Args:
            project_id (str)_
            package (str)
            sample_ids (List[str])
            user_type (str)
            other_user (str)

        """
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
        """_summary_

        Args:
            project_id (str)
            sample_ids (List[str])
            user_type (str)
            other_user (str)

        Returns:
            relation_table: {
                "root": { "_": { "ADJ": 1 } },
                "punct": { "ADP": { "PUNCT": 2 } },
                "mod": { "ADJ": { "ADV": 1 } },
                "comp:obj": { "ADP": { "ADJ": 1 } }
            }
        """
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
        """Get lexicon

        Args:
            project_name (str)
            sample_ids (List[str])
            user_type (str)
            other_user (str)
            prune (int)
            features (str)
        """
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
        """
            This function is used in grew search, try package, 
            relation table and lexicon to get user_ids parameter
            based on the user type and other user value

        Args:
            user_type (str)
            other_user (str)

        Returns:
            dict
        """
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
        """Insert conll in specific position

        Args:
            project_id (str)
            sample_id (str)
            pivot_sent_id (str)
            conll_file (File): contains conlls strings to insert
        """
        data = {
            "project_id": project_id,
            "sample_id": sample_id,
            "pivot_sent_id": pivot_sent_id
        }
        files = { "conll_file": conll_file }
        grew_request("insertConll", data=data, files=files)

    @staticmethod
    def erase_sentence(project_id: str, sample_id: str, sent_id: str):
        """erase sentence

        Args:
            project_id (str)
            sample_id (str)
            sent_id (str)
        """
        data = {
            "project_id": project_id,
            "sample_id": sample_id,
            "sent_id": sent_id
        }
        grew_request("eraseSentence", data=data)
        
    @staticmethod
    def extract_tagset(project_id, sample_ids, grew_funct):
        """Extract configuration tags based on conll 
        Args:
            project_id (str)
            sample_ids (List[str])
            grew_funct (str): getPos | getRelations | getFeatures

        Returns:
            _type_
        """
        data = {
            "project_id": project_id,
            "sample_ids": json.dumps(sample_ids)
        }
        response = grew_request(grew_funct, data=data)
        return response["data"]
    
    @staticmethod
    def get_config_from_samples(project_name, sample_ids):
        """Get all tags sets from list pf samples

        Args:
            project_name (str)
            sample_ids (str)

        Returns:
            post_list (List[str]), relation_list (List[str]), feat_list (List[str]), misc_list (List[str])
        """
        pos_list = GrewService.extract_tagset(project_name, sample_ids, "getPOS")
        relation_list = GrewService.extract_tagset(project_name, sample_ids, "getRelations")
        features = GrewService.extract_tagset(project_name, sample_ids, "getFeatures") 
        feat_list = features['FEATS']
        misc_list = features['MISC']
        return pos_list, relation_list, feat_list, misc_list

    @staticmethod
    def get_samples_with_string_contents(project_name: str, sample_names: List[str]):
        """Get string content od samples based on each user 

        Args:
            project_name (str)
            sample_names (List[str])

        Returns:
            samples_names (List[str]), sample_content_files [{'user_id': content_string }] 
        """
        sample_content_files = list()
        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":
                # {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
                sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
                sample_tree_nots_noui = SampleExportService.serve_sample_trees(reply.get("data", {}), timestamps=False, user_ids=False, validated_by=False)
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
                sample_content_files.append(sample_content)

            else:
                print("Error: {}".format(reply.get("message")))
        return sample_names, sample_content_files
    
    @staticmethod
    def get_samples_with_string_contents_as_dict(project_name: str, sample_names: List[str], user: str) -> Dict[str, str]:
        """Same as previous function but just for specific user

        Args:
            project_name (str)
            sample_names (List[str])
            user (str)

        Returns:
            Dict[str, str]
        """
        samples_dict_for_user: Dict[str, str] = {}
        for sample_name in sample_names:
            reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
            if reply.get("status") == "OK":

                # {"sent_id_1":{"conlls":{"user_1":"conllstring"}}}
                sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
                sample_tree_nots_noui = SampleExportService.serve_sample_trees(reply.get("data", {}), timestamps=False, user_ids=False, validated_by=False)
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
    def format_trees_new(m, trees, is_package: bool = False):
        """
            m is the query result from grew
            list of trees
            returns something like {'WAZL_15_MC-Abi_MG': {'WAZL_15_MC-Abi_MG__8': {'sentence': '# kalapotedly < you see < # ehn ...', 'conlls': {'kimgerdes': ...
        """

        user_id = m["user_id"]
        sample_name = m["sample_id"]
        sent_id = m["sent_id"]
        conll = m["conll"]

        if is_package == False:
            nodes = m["nodes"]
            edges = m["edges"]
        else:
            modified_nodes = m["modified_nodes"]
            modified_edges = m["modified_edges"]

        if sample_name not in trees:
            trees[sample_name] = {}

        if sent_id not in trees[sample_name]:
            try: 
                sentence_json = sentenceConllToJson(conll)
            except Exception as e:
                abort(400, 'The result of your query can not be processed by ArboratorGrew in sentence `{}` because: {}'.format(sent_id, str(e)))

            
            trees[sample_name][sent_id] = {
                "sentence": sentence_json["metaJson"]["text"],
                "conlls": {user_id: conll},
                "sent_id": sent_id,
            
            }
            if is_package == False:
                trees[sample_name][sent_id]["matches"] = {user_id: [{"edges": edges, "nodes": nodes}]}
            else:
                trees[sample_name][sent_id]["packages"] = {user_id: {"modified_edges": modified_edges, "modified_nodes": modified_nodes}}
        
        
        else:
            trees[sample_name][sent_id]["conlls"][user_id] = conll
            # /!\ there can be more than a single match for a same sample, sentence, user so it has to be a list
            if is_package == False:
                trees[sample_name][sent_id]["matches"][user_id] = trees[sample_name][sent_id][
                    "matches"
                ].get(user_id, []) + [{"edges": edges, "nodes": nodes}]
            else:
                trees[sample_name][sent_id]["packages"][user_id] = {"modified_edges": modified_edges, "modified_nodes": modified_nodes}
    
        return trees

def get_timestamp(conll):
    """Get timestamp metadat from conll string

    Args:
        conll (str)

    Returns:
        timestamp (str) | False
    """
    t = re.search(r"# timestamp = (\d+(?:\.\d+)?)\n", conll)
    if t and t.groups(): 
        return t.groups()[0]
    else:
        return False


class SampleExportService:
    """Class contains sample export functions"""
    @staticmethod
    def serve_sample_trees(samples, timestamps=True, user_ids=True, validated_by=True):
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
                if not validated_by: conll = re.sub("# validated_by = .+\n", '', conll)

                trees[sent_id]["conlls"][user_id] = conll
        return trees

    @staticmethod
    def sample_tree_to_content_file(tree) -> Dict[str, str]:
        """ 

        Args:
            tree (tree_object)

        Returns:
            Dict[str, str]
        """
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
        """Get username of most recent tree

        Args:
            tree (dict(str, str))

        Returns:
            username (str)
        """
        timestamps = [(user, get_timestamp(conll)) for (user, conll) in tree.items()]
        if len(timestamps) == 1:
            last = timestamps[0][0]
        else:
            last = sorted(timestamps, key=lambda x: x[1])[-1][0]
        return last

    @staticmethod
    def content_files_to_zip(sample_names, sample_trees, users):
        """convert files to export in zip file format

        Args:
            sample_names (List[str])
            sample_trees (List[{username: conll_content}, ...]): _description_
            users (List[str])

        Returns:
            memory_file (File)
        """
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w") as zf:
            for user in users:
                for sample_name, sample in zip(sample_names, sample_trees):
                    if user in sample.keys():
                        data = zipfile.ZipInfo()
                        data.filename = "{}/{}.conllu".format(user, sample_name) 
                        data.date_time = time.localtime(time.time())[:6]
                        data.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(data, sample.get(user))
        memory_file.seek(0)
        return memory_file