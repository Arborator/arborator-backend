import os
import re
from typing import List
import json

from app import klang_config

from app.utils.conllmaker import newtranscription

align_begin_and_end_regex = re.compile(
    r"^\d+\t(.+?)\t.*AlignBegin=(\d+).*AlignEnd=(\d+)"
)


class KlangService:
    @staticmethod
    def get_path_data():
        path_data = klang_config.path
        return path_data

    @staticmethod
    def get_path_project(project_name: str) -> str:
        path_data = KlangService.get_path_data()
        path_project = os.path.join(path_data, project_name)
        return path_project

    @staticmethod
    def get_path_project_config(project_name: str) -> str:
        path_project = KlangService.get_path_project(project_name)
        path_project_config = os.path.join(path_project, "config.json")
        return path_project_config

    @staticmethod
    def get_project_config(project_name: str):
        path_project_config = KlangService.get_path_project_config(project_name)
        with open(path_project_config, "r", encoding="utf-8") as infile:
            project_config = json.load(infile)
        return project_config
    
    @staticmethod
    def update_project_config(project_name, project_config):
        path_project_config = KlangService.get_path_project_config(project_name)
        with open(path_project_config, "w", encoding="utf-8") as outfile:
            outfile.write( json.dumps(project_config))

    @staticmethod
    def get_project_admins(project_name: str) -> List[str]:
        project_config = KlangService.get_project_config(project_name)
        admins = project_config["admins"]
        return admins

    @staticmethod
    def get_path_project_samples(project_name: str) -> str:
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
    def get_path_project_sample_mp3(project_name, sample_name) -> str:
        path_sample = KlangService.get_path_project_sample(project_name, sample_name)
        mp3_name = sample_name + ".mp3"
        path_sample_mp3 = os.path.join(path_sample, mp3_name)
        return path_sample_mp3

    @staticmethod
    def get_projects():
        return os.listdir(KlangService.get_path_data())

    @staticmethod
    def get_project_samples(project_name: str):
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


class TranscriptionService:
    @staticmethod
    def get_path_transcriptions(project_name, sample_name) -> str:
        path_project_sample = KlangService.get_path_project_sample(
            project_name, sample_name
        )
        path_transcriptions = os.path.join(path_project_sample, "transcriptions.json")
        return path_transcriptions

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
            outfile.write(json.dumps([]))

    @staticmethod
    def delete_transcriptions_file(project_name, sample_name):
        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        os.remove(path_transcriptions)

    @staticmethod
    def update_transcriptions_file(project_name, sample_name, new_transcriptions):
        if not TranscriptionService.check_if_transcriptions_exist(
            project_name, sample_name
        ):
            TranscriptionService.create_transcriptions_file(project_name, sample_name)

        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        with open(path_transcriptions, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(new_transcriptions))

    @staticmethod
    def load_transcriptions(project_name, sample_name):
        if not TranscriptionService.check_if_transcriptions_exist(
            project_name, sample_name
        ):
            TranscriptionService.create_transcriptions_file(project_name, sample_name)

        path_transcriptions = TranscriptionService.get_path_transcriptions(
            project_name, sample_name
        )
        with open(path_transcriptions, "r", encoding="utf-8") as infile:
            transcriptions = json.load(infile)
        
        transcriptions = TranscriptionService.validate_transcriptions(transcriptions)

        return transcriptions
    
    @staticmethod
    def validate_transcriptions(transcriptions):
        if type(transcriptions) != list:
            transcriptions = []
        
        return transcriptions

    @staticmethod
    def new_conll_from_transcription(original_conll, new_transcription, sample_name, soundfile_name):
        new_conll = newtranscription(original_conll, new_transcription, sample_name, soundfile_name)
        return new_conll