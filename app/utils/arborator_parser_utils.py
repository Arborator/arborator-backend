from typing import Dict, TypedDict, Union
import requests

from app import parser_config


class ModelInfo_t(TypedDict):
    project_name: str
    model_id: str

class ArboratorParserAPI:
    @staticmethod
    def send_get_request(url_suffix: str):
        url = f"{parser_config.server}/parser/models{url_suffix}"
        try:
            reply = requests.get(url, timeout=10)
            return reply.json()
        except requests.exceptions.ReadTimeout:
            return {"status": "failure", "error": f"<ArboratorParserAPI> connection timout with `url={url}`"}
        except Exception as e:
            print(f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}", e)
            return {"status": "failure", "error": f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}"}


    @staticmethod
    def send_post_request(url_suffix: str, data: Dict):
        url = f"{parser_config.server}/parser/models{url_suffix}"
        try:
            reply = requests.post(url, json=data, timeout=10)
            data = reply.json()
            if data.get("schema_errors"):
                return {
                    "status": "failure",
                    "error": f"<ArboratorParserSchemaValidation> You have a problem with at least one of the sentence "
                             f"you sent",
                    "schema_errors": data.get("schema_errors"),
                        }
            return data
        except requests.exceptions.ReadTimeout:
            return {"status": "failure", "error": f"<ArboratorParserAPI> connection timout with `url={url}`"}
        except Exception as e:
            print(f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}", e)
            return {"status": "failure", "error": f"<ArboratorParserAPI> unknown error when connecting `url={url}` : {str(e)}"}

    @staticmethod
    def list():
        return ArboratorParserAPI.send_get_request("/list")

    @staticmethod
    def train_start(project_name: str, train_samples: Dict[str, str], max_epoch: int, base_model: Union[ModelInfo_t, None]):
        data = {
            "project_name": project_name,
            "train_samples": train_samples,
            "max_epoch": max_epoch,
            "base_model": base_model,
        }
        return ArboratorParserAPI.send_post_request("/train/start", data)

    @staticmethod
    def train_status(model_info: ModelInfo_t, train_task_id: str):
        data = {
            "model_info": model_info,
            "train_task_id": train_task_id,
        }
        return ArboratorParserAPI.send_post_request("/train/status", data)

    @staticmethod
    def parse_start(model_info: ModelInfo_t, to_parse_samples: Dict[str, str], parse_settings: Dict[str, str]):
        data = {
            "model_info": model_info,
            "to_parse_samples": to_parse_samples,
            "parse_settings": parse_settings,
        }
        return ArboratorParserAPI.send_post_request("/parse/start", data)

    @staticmethod
    def parse_status(parse_task_id: str):
        data = {
            "parse_task_id": parse_task_id,
        }
        return ArboratorParserAPI.send_post_request("/parse/status", data)
