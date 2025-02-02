import os
from typing import TypedDict, List, Union

from flask import request, abort
from flask_restx import Namespace, Resource

from app.utils.grew_utils import GrewService
from app.config import Config
from ..samples.service import add_or_keep_timestamps, add_or_replace_userid
from ..projects.service import ProjectService, ProjectAccessService
from ..user.service import EmailService
from ..utils.arborator_parser_utils import ArboratorParserAPI, ModelInfo_t

api = Namespace("Parser", description="Endpoints for dealing with the parser")  # noqa


@api.route("/list")
class ParserModelsListResource(Resource):
    def get(self):
        """Get list of available models in GPU server

        Returns:
            { "status": "ok", "data": list_parser (List[parser]) }
        """
        print("<PARSER> list/start request")
        response =  ArboratorParserAPI.list()
        if response['status'] == 'failure':
            error_message = 'Sorry, the parsing server is unreachable, please come back later'
            EmailService.send_alert_email('Parsing server', error_message)
            abort(503, error_message)
        else: 
            pretrained_models = []
            models = response.get("data")
            for model in models:
                project_name = model['model_info']['project_name']
                project = ProjectService.get_by_name(project_name)
                if project != None:
                    if ProjectAccessService.check_project_access(project.visibility, project.id):
                        pretrained_models.append({
                            **model, 
                            "language": project.language, 
                            "admins": ProjectAccessService.get_admins(project.id) 
                        })
            return { "status": "success",  "data": pretrained_models }

@api.route("/list/<string:project_name>/<string:model_id>")       
class ParserModelIdResource(Resource): 
    def delete(self, project_name: str, model_id: str):
        """Delete model from GPU server"""
        print("<PARSER> list/model_id  delete request", project_name, model_id)
        return ArboratorParserAPI.delete_model(project_name, model_id)
        
          
class ParserTrainStart_ED(TypedDict):
    """Typed interface to start train request"""
    project_name: str
    train_samples_names: List[str]
    train_user: str
    max_epoch: int
    base_model: Union[None, ModelInfo_t]

@api.route("/train/start")
class ParserTrainStartResource(Resource):
    def post(self):
        """Start train request"""
        params: ParserTrainStart_ED = request.get_json(force=True)
        print("<PARSER> train/start request :", params)
        project_name = params["project_name"]
        train_samples_names = params["train_samples_names"]
        train_user = params["train_user"]
        max_epoch = params["max_epoch"]
        base_model = params["base_model"]

        if project_name == "undefined":
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        train_samples = GrewService.get_samples_with_string_contents_as_dict(project_name, train_samples_names, train_user)

        return ArboratorParserAPI.train_start(project_name, train_samples, max_epoch, base_model)


@api.route("/train/status")
class ParserTrainStatusResource(Resource):
    def post(self):
        """Get training status this request is send every 10 seconds after starting the parsing"""
        params = request.get_json(force=True)

        print("<PARSER> parser/info request :", params)

        train_task_id = params["train_task_id"]
        model_info = params["model_info"]
        project_name = model_info["project_name"]

        if project_name == "undefined":
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        return ArboratorParserAPI.train_status(model_info, train_task_id)



@api.route("/parse/start")
class ParserParseStartResource(Resource):
    def post(self):
        """Start parsing endpoint"""
        params = request.get_json(force=True)
        print("<PARSER> parse/start request :", params)

        to_parse_samples_names = params["to_parse_samples_names"]
        project_name = params["project_name"]
        model_info = params["model_info"]
        parsing_user = params["parsing_user"]
        parsing_settings = params["parsing_settings"]
        if project_name == "undefined":
            return {"status": "failure", "error": "NOT VALID PROJECT NAME"}

        to_parse_samples = GrewService.get_samples_with_string_contents_as_dict(project_name, to_parse_samples_names, parsing_user)

        return ArboratorParserAPI.parse_start(model_info, to_parse_samples, parsing_settings)


@api.route("/parse/status")
class ParserParseStatus(Resource):
    def post(self):
        """Get parsing status, this request is also send every 10s after start parsing"""
        params = request.get_json(force=True)
        print("<PARSER> parse/status request :", params)

        model_info = params["model_info"]
        project_name = params["project_name"]
        parse_task_id = params["parse_task_id"]
        parser_suffix = params["parser_suffix"]

        if project_name == "undefined":
            return {"status": "NOT VALID PROJECT NAME"}

        parse_status_reply = ArboratorParserAPI.parse_status(parse_task_id)
        if parse_status_reply["status"] == "failure":
            return parse_status_reply

        data = parse_status_reply["data"]
        if data.get("ready") and data.get("parsed_samples"):
            task_model_info = data["model_info"]
            task_parsed_samples = data["parsed_samples"]

            if task_model_info["model_id"] == model_info["model_id"] and task_model_info["project_name"] == model_info["project_name"]:

                for sample_name, sample_content in task_parsed_samples.items():
                    path_file = os.path.join(Config.UPLOAD_FOLDER, sample_name)
                    print('upload parsed\n', path_file)
                    with open(path_file,'w') as f:
                        f.write(sample_content)

                    add_or_keep_timestamps(path_file, when="long_ago")
                    add_or_replace_userid(path_file, "parser" + parser_suffix)
                    with open(path_file, "rb") as file_to_save:
                        print('save files')
                        GrewService.save_sample(project_name, sample_name, file_to_save)
                    os.remove(path_file)
                    
            del data["parsed_samples"]

        return {"status": "success", "data": data}





