import os
from os import stat
import re
from typing import List
from sqlalchemy import exc
import sys
import json
from flask import abort

from app import klang_config, db
from .model import Transcription
from app.user.model import User
from flask_login import current_user

align_begin_and_end_regex = re.compile(
    r"^\d+\t(.+?)\t.*AlignBegin=(\d+).*AlignEnd=(\d+)"
)


class KlangService:
    @staticmethod
    def get_path_data():
        path_data = klang_config.path
        return path_data

    @staticmethod
    def get_path_project(project_name) -> str:
        path_data = KlangService.get_path_data()
        path_project = os.path.join(path_data, project_name)
        return path_project

    @staticmethod
    def get_path_project_samples(project_name) -> str:
        path_project = KlangService.get_path_project(project_name)
        path_samples = os.path.join(path_project, "samples")
        return path_samples

    @staticmethod
    def get_path_project_sample(project_name, sample_name) -> str:
        path_project_samples = KlangService.get_path_project_samples(project_name)
        path_project_sample = os.path.join(path_project_samples, sample_name)
        return path_project_sample

    @staticmethod
    def get_path_project_sample_conll(project_name, sample_name) -> str:
        path_sample = KlangService.get_path_project_sample(project_name, sample_name)
        conll_name = sample_name + ".intervals.conll"
        path_sample_conll = os.path.join(path_sample, conll_name)
        return path_sample_conll

    @staticmethod
    def get_projects():
        return os.listdir(KlangService.get_path_data())

    @staticmethod
    def get_project_samples(project_name):
        return os.listdir(KlangService.get_path_project_samples(project_name))

    @staticmethod
    def read_conll(path_conll):
        with open(path_conll, "r", encoding="utf-8") as infile:
            conll = infile.read()
        return conll

    @staticmethod
    def get_project_sample_conll(project_name, sample_name):
        path_conll = KlangService.get_path_project_sample_conll(
            project_name, sample_name
        )
        conll_str = KlangService.read_conll(path_conll)
        return conll_str

    # @staticmethod
    # def get_all_name():
    #     path_data = KlangService.get_path_data()
    #     conlls = os.listdir(path_data)
    #     return conlls

    # @staticmethod
    # def get_by_name(conll_name):
    #     path_conll = KlangService.get_path_conll(conll_name)
    #     conll = KlangService.read_conll(path_conll)
    #     return conll

    @staticmethod
    def conll_to_sentences(conll: str) -> List[str]:
        return list(filter(lambda x: x != "", conll.split("\n\n")))

    @staticmethod
    def sentence_to_audio_tokens(sentence: str):
        audio_tokens = []
        for line in sentence.split("\n"):
            if line:
                if not line.startswith("#"):
                    m = align_begin_and_end_regex.search(line)
                    audio_token = [m.group(1), m.group(2), m.group(3)]
                    audio_tokens.append(audio_token)

        return audio_tokens

    @staticmethod
    def compute_conll_audio_tokens(conll: str):
        sentences = KlangService.conll_to_sentences(conll)
        conll_audio_tokens = []
        for sentence in sentences:
            audio_tokens = KlangService.sentence_to_audio_tokens(sentence)
            conll_audio_tokens.append(audio_tokens)
        return conll_audio_tokens

    # @staticmethod
    # def process_sentences_audio_token(conll_name: str):
    #     conll = KlangService.get_project_sample_conll(conll_name)
    #     sentences = KlangService.conll_to_sentences(conll)
    #     sentences_audio_token = []
    #     for sentence in sentences:
    #         audio_tokens = KlangService.sentence_to_audio_tokens(sentence)
    #         sentences_audio_token.append(audio_tokens)
    #     return sentences_audio_token

    @staticmethod
    def get_transcription(user_name, conll_name):
        result = {
            "transcription": [],
        }
        try:
            record = Transcription.query.filter_by(user=user_name, mp3=conll_name).one()
            trans = json.loads(record.transcription)
            result["transcription"] = trans
            result["sound"] = record.sound
            result["story"] = record.story
            result["accent"] = record.accent
            result["monodia"] = record.monodia
            result["title"] = record.title
            pass
        except exc.SQLAlchemyError:
            print(sys.exc_info()[0])
            pass
        return result

    @staticmethod
    def get_users_list(is_admin):
        users = []
        if is_admin == "true":
            users = [x.username for x in User.query.all()]
        elif current_user.is_authenticated:
            users = [current_user.username]
        return users

    @staticmethod
    def save_transcription(
        conll_name, transcription, sound, story, accent, monodia, title
    ):
        user_name = current_user.username
        try:
            Transcription.query.filter_by(user=user_name, mp3=conll_name).delete(
                synchronize_session=False
            )
            trans_str = json.dumps(transcription)
            record = Transcription(
                user=user_name,
                mp3=conll_name,
                transcription=trans_str,
                sound=sound,
                story=story,
                accent=accent,
                monodia=monodia,
                title=title,
            )
            db.session.add(record)
            db.session.commit()
            pass
        except:
            print(sys.exc_info()[0])
            db.session.rollback()
            abort(400)
            pass


class TranscriptionService:
    @staticmethod
    def get_path_transcriptions(project_name, sample_name) -> str:
        path_project_sample = KlangService.get_path_project_sample(
            project_name, sample_name
        )
        path_transcriptions = os.path.join(path_project_sample, "transcriptions.json")
        return path_transcriptions

    @staticmethod
    def load_transcriptions(project_name, sample_name):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        with open(path_transcriptions, "r", encoding="utf-8") as infile:
            transcriptions = json.load(infile)
        return transcriptions

    @staticmethod
    def check_if_transcriptions_exist(project_name, sample_name):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        return os.path.isfile(path_transcriptions)

    @staticmethod
    def create_transcriptions_file(project_name, sample_name):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        with open(path_transcriptions, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps({}))

    @staticmethod
    def delete_transcriptions_file(project_name, sample_name):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        os.remove(path_transcriptions)

    @staticmethod
    def update_transcriptions_file(project_name, sample_name, new_transcriptions):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        with open(path_transcriptions, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(new_transcriptions))
