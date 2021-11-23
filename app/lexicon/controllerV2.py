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

    @responds(schema=LexiconItemSchema(many=True), api=api)
    def post(self, project_name: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="samplenames", type=str, action="append")
        parser.add_argument(name="treeSelection", type=str)
        args = parser.parse_args()

        sample_names = args.get("samplenames")
        treeSelection = args.get("treeSelection")
        reply = grew_request(
            "getLexicon",
            data={"project_id": project_name, "sample_ids": json.dumps(sample_names)},
        )
        lexiconItems: List[LexiconItemInterface] = []
        for lexiconItemGrew in reply["data"]:
            lexiconItem = LexiconItemInterface(
                form=lexiconItemGrew["form"],
                lemma=lexiconItemGrew["lemma"],
                pos=lexiconItemGrew["POS"],
                gloss=lexiconItemGrew["gloss"],
                features=TokenProcessor.conll_mapping_to_dict_mapping(
                    lexiconItemGrew.get("features", "_")
                ),  # for now, grew send features as a string (conll format)
                frequency=lexiconItemGrew["frequency"],
            )
            lexiconItems.append(lexiconItem)

        return lexiconItems
