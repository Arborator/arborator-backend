from flask import request, abort
from flask_restx import Namespace, Resource
from flask import request, current_app
from flask_login import current_user

from .service import KlangService


api = Namespace("Klang", description="Single namespace, single entity")  # noqa


@api.route("/projects")
class ProjectsServiceResource(Resource):
    "Klang projects"

    def get(self):
        return KlangService.get_projects()


@api.route("/projects/<string:project_name>/samples")
class SamplesServiceResource(Resource):
    "Klang samples (by project)"

    def get(self, project_name):
        return KlangService.get_project_samples(project_name)


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/timed-tokens")
class TimedTokensServiceResource(Resource):
    "Timed tokens"

    def get(self, project_name, sample_name):
        path_conll = KlangService.get_path_project_sample_conll(
            project_name, sample_name
        )
        conll = KlangService.read_conll(path_conll)
        conll_audio_tokens = KlangService.compute_conll_audio_tokens(conll)
        return conll_audio_tokens


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/tanscription")
class TranscriptionServiceResource(Resource):
    "Transcriptions"

    def get(self, project_name, sample_name):
        path_conll = KlangService.get_path_project_sample_conll(
            project_name, sample_name
        )
        conll = KlangService.read_conll(path_conll)
        conll_audio_tokens = KlangService.compute_conll_audio_tokens(conll)
        response = {"original": conll_audio_tokens}
        return response


# @api.route("/projects/<string:project_name>/samples/<string:sample_name>/tanscription-all")
# class TranscriptionServiceResource(Resource):
#     "Transcriptions"

#     def get


# @api.route("/conlls")
# class KlangServiceResource(Resource):
#     "KlangService"

#     def get(self):
#         return KlangService.get_all_name()


@api.route("/conlls/<string:conll_name>")
class ConllNameServiceResource(Resource):
    "KlangService"

    def get(self, conll_name):
        conll_string = KlangService.get_by_name(conll_name)
        sentences_string = KlangService.conll_to_sentences(conll_string)
        sentences_audio_token = []
        is_admin = request.args.get("is_admin")
        users = KlangService.get_users_list(is_admin)
        response = {}

        for sentence_string in sentences_string:
            audio_tokens = KlangService.sentence_to_audio_tokens(sentence_string)
            sentences_audio_token.append(audio_tokens)
        response["original"] = sentences_audio_token
        if not current_user.is_authenticated:
            return response

        for user in users:
            transcription = KlangService.get_transcription(user, conll_name)

            if transcription["transcription"] != [] or user == current_user.username:
                response[user] = transcription

        return response

    def post(self, conll_name):
        # check if the user is logged in
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        data = request.get_json()
        transcription = data["transcription"]
        sound = data["sound"]
        story = data["story"]
        accent = data["accent"]
        monodia = data["monodia"]
        title = data["title"]

        if not transcription:
            abort(400)

        KlangService.save_transcription(
            conll_name,
            transcription,
            sound,
            story,
            accent,
            monodia,
            title,
        )
        return data