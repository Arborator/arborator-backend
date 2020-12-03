import io
import os
from os import path

from app.klang.interface import TranscriptionInterface
from app.klang.schema import TranscriptionSchema
from app.shared.service import SharedService
from flask import abort, current_app, request
from flask.helpers import send_file, send_from_directory
from flask_accepts.decorators.decorators import accepts, responds
from flask_login import current_user
from flask_restx import Namespace, Resource, reqparse

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


@api.route("/projects/<string:project_name>/admins")
class ProjectAdminsServiceResource(Resource):
    "Klang admins (by project)"

    def get(self, project_name):
        "get all admins of a project"
        return KlangService.get_project_admins(project_name)

    def post(self, project_name):
        "post a list of admins (replace the old one)"
        parser = reqparse.RequestParser()
        parser.add_argument(name="admins", type=str, action="append")
        args = parser.parse_args()
        admins = args.get("admins")

        project_config = KlangService.get_project_config(project_name)
        project_config["admins"] = admins
        KlangService.update_project_config(project_name, project_config)

        return admins


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


@api.route(
    "/projects/<string:project_name>/samples/<string:sample_name>/transcriptions"
)
class TranscriptionsServiceResource(Resource):
    "Transcriptions"

    def get(self, project_name, sample_name):
        "get the transcriptions of all users"
        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        return transcriptions


@api.route(
    "/projects/<string:project_name>/samples/<string:sample_name>/transcription/<string:username>"
)
class TranscriptionUserServiceResource(Resource):
    "Transcription for one user"

    @responds(schema=TranscriptionSchema, api=api)
    def get(self, project_name, sample_name, username):
        "get the transcription of a user"
        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        transcription = next(
            filter(lambda x: x["user"] == username, transcriptions), {}
        )
        return transcription

    @accepts(schema=TranscriptionSchema, api=api)
    def put(self, project_name, sample_name, username):
        "create/update the transcription of a user"
        if not current_user.is_authenticated or current_user.username != username:
            return current_app.login_manager.unauthorized()

        data: TranscriptionInterface = request.parsed_obj

        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        transcription = next(
            filter(lambda x: x["user"] == username, transcriptions), None
        )
        if transcription == None:
            transcriptions.append(data)
        else:
            transcription.update(data)

        TranscriptionService.update_transcriptions_file(
            project_name, sample_name, transcriptions
        )
        return data


@api.route("/projects/<string:project_name>/samples/<string:sample_name>/mp3")
class Mp3ServiceResource(Resource):
    "MP3 Resources"

    def get(self, project_name, sample_name):
        "get the mp3 for a given sample"
        path_project_sample = KlangService.get_path_project_sample(
            project_name, sample_name
        )
        mp3_filename = sample_name + ".mp3"

        return send_file(
            os.path.join(path_project_sample, mp3_filename), conditional=True
        )


@api.route(
    "/projects/<string:project_name>/samples/<string:sample_name>/export-conll/<string:username>"
)
class ExportConllServiceResource(Resource):
    "Export Conll Resources"

    def get(self, project_name, sample_name, username):
        "download the conll (as attachement) with the transcription of a user"
        path_original_conll = KlangService.get_path_project_sample_conll(
            project_name, sample_name
        )
        transcriptions = TranscriptionService.load_transcriptions(
            project_name, sample_name
        )
        transcription = next(
            filter(lambda x: x["user"] == username, transcriptions),
            None,
        )
        if not transcription:
            abort(403, f"transcription for user '{username}' was not found")

        new_transcription = transcription["transcription"]

        new_conll = TranscriptionService.new_conll_from_transcription(
            path_original_conll,
            new_transcription,
            sample_name,
            f"{sample_name}.mp3",
        )

        new_conll_name = f"{sample_name}.{username}.intervals.conll"

        sendable_new_conll = SharedService.get_sendable_data(new_conll)

        return send_file(
            sendable_new_conll, attachment_filename=new_conll_name, as_attachment=True
        )
