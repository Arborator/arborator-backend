from datetime import datetime
from typing import List

from flask import session
from flask_accepts.decorators.decorators import responds
from flask_restx import Namespace, Resource

from .service import ConllService

api = Namespace("Klang", description="Single namespace, single entity")  # noqa

@api.route("/conlls")
class ConllServiceResource(Resource):
    "ConllService"

    def get(self) :
        return ConllService.get_all()


@api.route("/conll/<string:conll_name>")
class ConllNameServiceResource(Resource):
    "ConllService"

    def get(self, conll_name) :
        conll_string = ConllService.get_by_name(conll_name)
        sentences_string = ConllService.seperate_conll_sentences(conll_string)
        sentences_audio_token = []
        for sentence_string in sentences_string:
          audio_tokens = ConllService.sentence_to_audio_tokens(sentence_string)
          sentences_audio_token.append(audio_tokens)
        return sentences_audio_token