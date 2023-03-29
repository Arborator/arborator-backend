from typing import Dict
import requests

from app import parser_config


class ArboratorParserAPI:
    @staticmethod
    def send_post_request(url_suffix: str, data: Dict):
        url = f"{parser_config.server}/parser/models{url_suffix}"
        try:
            reply = requests.post(url, json=data, timeout=10)
            return reply.json()
        except requests.exceptions.ReadTimeout:
            return {"status": "failure", "error": f"<ArboratorParserAPI> connection timout with `url={url}`"}
        except Exception as e:
            print(f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}", e)
            return {"status": "failure", "error": f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}"}

    @staticmethod
    def train_start(project_name: str, train_samples: Dict[str, str], max_epoch: int):
        data = {
            "project_name": project_name,
            "train_samples": train_samples,
            "max_epoch": max_epoch,
        }
        return ArboratorParserAPI.send_post_request("/train/start", data)

    @staticmethod
    def train_status(project_name: str, model_id: str):
        data = {
            "project_name": project_name,
            "model_id": model_id,
        }
        return ArboratorParserAPI.send_post_request("/train/status", data)

    @staticmethod
    def parse_start(project_name: str, model_id: str, to_parse_samples: Dict[str, str]):
        data = {
            "project_name": project_name,
            "model_id": model_id,
            "to_parse_samples": to_parse_samples,
        }
        return ArboratorParserAPI.send_post_request("/parse/start", data)

    @staticmethod
    def parse_status(parse_task_id: str):
        data = {
            "parse_task_id": parse_task_id,
        }
        return ArboratorParserAPI.send_post_request("/parse/status", data)
