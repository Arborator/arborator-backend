import json

from flask import request
from flask import Response
from flask_restx import Namespace, Resource

from app.utils.grew_utils import GrewService

api = Namespace(
    "LexiconV2", description="Endpoints for dealing with samples of project"
)


@api.route("/<string:project_name>/lexicon")
class LexiconResource(Resource):
    "Lexicon"

    def post(self, project_name: str):
        
        args = request.get_json()
        sample_ids = args.get("samplenames")
        features = args.get("features")
        lexicon_type = args.get("lexiconType")
        prune = args.get("prune")
        
        reply = GrewService.get_lexicon(project_name, sample_ids, lexicon_type, '',prune, features)
        return reply["data"]


@api.route("/lexicon/export-json")	
class LexiconExportJson(Resource):	
    def post(self):	

        args = request.get_json()	
        lexicon = args.get("data")	
        for element in lexicon:	
            del element["key"]	
        line = json.dumps(lexicon, separators=(",", ":"), indent=4)	
        resp = Response(line, status=200)	
        return resp
    

@api.route("/lexicon/export-tsv")	
class LexiconExportTsv(Resource):	
    def post(self):	
        
        args = request.get_json()
        lexicon = args.get("data")	
        
        features = list(lexicon[0]["feats"].keys())	
        header = "\t".join(features)+"\tfrequence"	
        line_tsv = header+'\n'	

        for item in lexicon:	
            line_tsv += "\t".join(str(value) for key, value in item["feats"].items())	
            line_tsv += "\t"+str(item["freq"])	
            line_tsv += "\n"	
        return line_tsv