from datetime import datetime
from typing import List

from flask import session, request, abort
from flask_accepts.decorators.decorators import responds
from flask_restx import Namespace, Resource, reqparse
from flask import request, current_app

from .service import ConllService
from flask_login import current_user, login_required
import requests

api = Namespace("Klang", description="Single namespace, single entity")  # noqa


@api.route("/conlls")
class ConllServiceResource(Resource):
    "ConllService"

    def get(self):
        # check if the user is logged in
        if not current_user.is_authenticated:  
            return current_app.login_manager.unauthorized()
        return ConllService.get_all()


@api.route("/conlls/<string:conll_name>")
class ConllNameServiceResource(Resource):
    "ConllService"

    def get(self, conll_name):
        # check if the user is logged in
        if not current_user.is_authenticated:  
            return current_app.login_manager.unauthorized()
        conll_string = ConllService.get_by_name(conll_name)
        sentences_string = ConllService.seperate_conll_sentences(conll_string)
        sentences_audio_token = []
        is_admin = request.args.get('is_admin')
        users = ConllService.get_users_list(is_admin)
        response = {}

        for sentence_string in sentences_string:
            audio_tokens = ConllService.sentence_to_audio_tokens(
                sentence_string)
            sentences_audio_token.append(audio_tokens)
        response['original'] = sentences_audio_token
        for user in users:
            transcription = ConllService.get_transcription(
                user, conll_name,  sentences_audio_token)
            response[user] = transcription
        
        return response

    def post(self, conll_name):
        data = request.get_json()
        transcription = data['transcription']
        if not transcription:
            abort(400)
        ConllService.save_transcription(conll_name, transcription)
        return {'transcription': transcription}