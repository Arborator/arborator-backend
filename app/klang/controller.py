import os

from flask.helpers import send_file
from app.klang.interface import TranscriptionInterface
from app.klang.schema import TranscriptionSchema
from flask import abort, current_app, request
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource

from .service import KlangService, TranscriptionService

api = Namespace("Klang", description="Single namespace, single entity")  # noqa


@api.route("/projects")
class ProjectsServiceResource(Resource):
    "Klang projects"

    def get(self):
        "get all projects on klang database"
        return KlangService.get_projects()


@api.route("/projects/<string:project_name>/samples")
class SamplesServiceResource(Resource):
    "Klang samples (by project)"

    def get(self, project_name):
        "get all samples of a project"
        return KlangService.get_project_samples(project_name)


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/timed-tokens")
class TimedTokensServiceResource(Resource):
    "Timed tokens"

    def get(self, project_name, sample_name):
        "get the (original) timed-tokens assiociated to a conll"
        path_conll = KlangService.get_path_project_sample_conll(
            project_name, sample_name
        )
        conll = KlangService.read_conll(path_conll)
        conll_audio_tokens = KlangService.compute_conll_audio_tokens(conll)
        return conll_audio_tokens


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/transcriptions")
class TranscriptionsServiceResource(Resource):
    "Transcriptions"

    def get(self, project_name, sample_name):
        "get the transcriptions of all users"
        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        return transcriptions

    @accepts(schema=TranscriptionSchema, api=api)
    def post(self, project_name, sample_name):
        "create/update the transcription of a user"
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

        user = current_user.username
        user_trancription: TranscriptionInterface = request.parsed_obj

        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        transcriptions[user] = user_trancription

        TranscriptionService.update_transcriptions_file(
            project_name, sample_name, transcriptions
        )
        return user_trancription


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/transcription/<string:username>")
class TranscriptionUserServiceResource(Resource):
    "Transcription for one user"

    @responds(schema=TranscriptionSchema, api=api)
    def get(self, project_name, sample_name, username):
        "get the transcription of a user"
        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        transcription_user = transcriptions.get(username, {})
        return transcription_user

    # @accepts(schema=TranscriptionSchema, api=api)
    # def put(self, project_name, sample_name):
    #     if not current_user.is_authenticated:
    #         return current_app.login_manager.unauthorized()
    #     user = current_user.username
    #     user_trancription: TranscriptionInterface = request.parsed_obj

    #     transcriptions = TranscriptionService.load_transcriptions(
    #         project_name, sample_name
    #     )
    #     transcriptions[user] = user_trancription

    #     TranscriptionService.update_transcriptions_file(
    #         project_name, sample_name, transcriptions
    #     )
    #     return user_trancription



@api.route("/projects/<string:project_name>/samples/<string:sample_name>/mp3")
class Mp3ServiceResource(Resource):
    "MP3 Resources"

    def get(self, project_name, sample_name):
        "get the mp3 for a given sample"
        path_project_sample = KlangService.get_path_project_sample(project_name, sample_name)
        path_mp3 = os.path.join(path_project_sample, sample_name + ".mp3")
        return send_file(path_mp3)


# @api.route("/projects/<string:project_name>/samples/<string:sample_name>/transcription-all")
# class TranscriptionServiceResource(Resource):
#     "Transcriptions"

#     def get


# @api.route("/conlls")
# class KlangServiceResource(Resource):
#     "KlangService"

#     def get(self):
#         return KlangService.get_all_name()


# @api.route("/conlls/<string:conll_name>")
# class ConllNameServiceResource(Resource):
#     "KlangService"

#     def get(self, conll_name):
#         conll_string = KlangService.get_by_name(conll_name)
#         sentences_string = KlangService.conll_to_sentences(conll_string)
#         sentences_audio_token = []
#         is_admin = request.args.get("is_admin")
#         users = KlangService.get_users_list(is_admin)
#         response = {}

#         for sentence_string in sentences_string:
#             audio_tokens = KlangService.sentence_to_audio_tokens(sentence_string)
#             sentences_audio_token.append(audio_tokens)
#         response["original"] = sentences_audio_token
#         if not current_user.is_authenticated:
#             return response

#         for user in users:
#             transcription = KlangService.get_transcription(user, conll_name)

#             if transcription["transcription"] != [] or user == current_user.username:
#                 response[user] = transcription

#         return response

#     def post(self, conll_name):
#         # check if the user is logged in
#         if not current_user.is_authenticated:
#             return current_app.login_manager.unauthorized()
#         data = request.get_json()
#         transcription = data["transcription"]
#         sound = data["sound"]
#         story = data["story"]
#         accent = data["accent"]
#         monodia = data["monodia"]
#         title = data["title"]

#         if not transcription:
#             abort(400)

#         KlangService.save_transcription(
#             conll_name,
#             transcription,
#             sound,
#             story,
#             accent,
#             monodia,
#             title,
#         )
#         return data
