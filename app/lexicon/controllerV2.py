import json
from typing import List

from app.lexicon.interfaceV2 import LexiconItemInterface
from app.lexicon.schemaV2 import LexiconItemSchema
from app.utils.conllup import TokenProcessor
from app.utils.grew_utils import grew_request
from flask_accepts.decorators.decorators import responds
from flask_restx import Namespace, Resource, reqparse

api = Namespace(
    "LexiconV2", description="Endpoints for dealing with samples of project"
)


@api.route("/<string:project_name>/lexicon")
class LexiconResource(Resource):
    "Lexicon"

    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="samplenames", type=str, action="append")
        parser.add_argument(name="treeSelection", type=str)
        args = parser.parse_args()

        sample_names = args.get("samplenames")
        treeSelection = args.get("treeSelection")
        
        user_ids = "all"
        features = ["form", "lemma", "upos", "Gloss"]
        
        reply = grew_request(
            "getLexicon",
            data={"project_id": project_name, "sample_ids": json.dumps(sample_names), "user_ids": json.dumps(user_ids), "features": json.dumps(features),},
        )
        return reply["data"]
