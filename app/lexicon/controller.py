import json

from flask_login import current_user
from flask import Response
from flask_restx import Namespace, Resource, reqparse

from app.lexicon.interface import LexiconItemInterface
from app.lexicon.schema import LexiconItemSchema
from app.utils.grew_utils import grew_request

api = Namespace(
    "LexiconV2", description="Endpoints for dealing with samples of project"
)


@api.route("/<string:project_name>/lexicon")
class LexiconResource(Resource):
    "Lexicon"

    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="samplenames", type=str, action="append")
        parser.add_argument(name="features", type=str,action="append")
        parser.add_argument(name="lexiconType", type=str)
        parser.add_argument(name="prune", type=int)
        args = parser.parse_args()

        sample_names = args.get("samplenames")
        features = args.get("features")
        lexicon_type=args.get("lexiconType")
        prune=args.get("prune")
       
        if lexicon_type == 'user':
            user_ids = { "one": [current_user.username] }
        elif lexicon_type == 'user_recent':
            user_ids = { "one": [current_user.username, "__last__"] }
        elif lexicon_type == 'recent':
            user_ids = { "one": ["__last__"] }
        elif lexicon_type == 'validated':
            user_ids = { "one": ["Validated"] } 
        elif lexicon_type=='all':
            user_ids = "all"

        prune = (None, prune) [prune != 0]
        reply = grew_request(
            "getLexicon",
            data={"project_id": project_name, "sample_ids": json.dumps(sample_names), "user_ids": json.dumps(user_ids), "features": json.dumps(features),"prune":prune},
        )
        return reply["data"]


@api.route("/<string:project_name>/lexicon/export-json")	
class LexiconExportJson(Resource):	
    def post(self, project_name: str):	
        parser = reqparse.RequestParser()	
        parser.add_argument(name="data", type=dict, action="append")	
        args = parser.parse_args()	

        lexicon = args.get("data")	
        for element in lexicon:	
            del element["key"]	
        line = json.dumps(lexicon, separators=(",", ":"), indent=4)	
        resp = Response(line, status=200)	
        return resp
    

@api.route("/<string:project_name>/lexicon/export-tsv")	
class LexiconExportTsv(Resource):	
    def post(self, project_name: str):	
        parser = reqparse.RequestParser()	
        parser.add_argument(name="data", type=dict, action="append")	
        args = parser.parse_args()	
        lexicon = args.get("data")	

        features=list(lexicon[0]["feats"].keys())	
        header = "\t".join(features)+"\tfrequence"	
        line_tsv=header+'\n'	

        for item in lexicon:	
            line_tsv += "\t".join(str(value) for key, value in item["feats"].items())	
            line_tsv += "\t"+str(item["freq"])	
            line_tsv += "\n"	