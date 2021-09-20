# Some utility functions for grew process
import json
from typing import Dict, List

import requests
from flask import abort, current_app
from werkzeug.utils import secure_filename
from app import grew_config


def grew_request(fct_name, data={}, files={}):
    try:
        response = requests.post("%s/%s" % (grew_config.server, fct_name), files=files, data=data)

    except requests.ConnectionError:
        error_message = "<Grew requests handler> : Connection refused"
        print(error_message)
        abort(500, {"message": error_message})

    except Exception as e:
        error_message = (
            "Grew requests handler> : Uncaught exception, please report {}".format(e)
        )
        print(error_message)
        abort(500, {"message": error_message})
    response = json.loads(response.text)
    if response.get("status") != "OK":
        if "data" in response:
            message = str(response["data"])
        elif "message" in response:
            message = str(response["message"])
        else:
            message = "unknown grew servor error"

        response = {"message": message}
        abort(400, response)

    return response


class GrewService:
    @staticmethod
    def get_sample_trees(projectName, sampleName) -> Dict[str, Dict[str, str]]:
        response = grew_request(
            "getConll",
            data={"project_id": projectName, "sample_id": sampleName},
        )
        grew_sample_trees: Dict[str, Dict[str, str]] = response.get("data", {})
        return grew_sample_trees

    @staticmethod
    def get_projects():
        reply = grew_request("getProjects")
        grew_projects = reply.get("data", [])
        return grew_projects

    @staticmethod
    def create_project(project_id: str) -> None:
        grew_request(
            "newProject",
            data={"project_id": project_id},
        )
        return

    @staticmethod
    def delete_project(project_id: str) -> None:
        grew_request("eraseProject", data={"project_id": project_id})
        return

    @staticmethod
    def get_project_config(project_id: str):
        grew_reply = grew_request("getProjectConfig", data={"project_id": project_id})
        # TODO : redo this. It's ugly
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
        return


    @staticmethod
    def get_samples(project_id : str):
        reply = grew_request(
            "getSamples", data={"project_id": project_id}
        )
        grew_samples = reply.get("data", [])

        return grew_samples
    
    @staticmethod
    def create_sample(project_id: str, sample_id: str):
        reply = grew_request(
            "newSample",
            data={"project_id": project_id, "sample_id": sample_id},
        )

        return reply

    
    @staticmethod
    def save_sample(project_id: str, sample_id: str, conll_file) -> None:
        grew_request(
            "saveConll",
            data={"project_id": project_id, "sample_id": sample_id},
            files={"conll_file": conll_file},
        )
        return

    @staticmethod
    def delete_sample(project_id: str, sample_id: str) -> None:
        grew_request(
            "eraseSample",
            data={"project_id": project_id, "sample_id": sample_id},
        )

    @staticmethod
    def search_pattern_in_graphs(project_id: str, pattern: str, user_ids = []):
        data = {
            "project_id": project_id,
            "pattern": pattern,
            "user_ids": "[{}]".format(",".join(user_ids)),
        }
        reply = grew_request("searchPatternInGraphs", data=data)
        return reply
