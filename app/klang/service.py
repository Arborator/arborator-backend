import os
import re
from typing import List
import json

from app import klang_config

from app.utils.conllmaker import newtranscription
from app.user.service import UserService

align_begin_and_end_regex = re.compile(
    r"^\d+\t(.+?)\t.*AlignBegin=(\d+).*AlignEnd=(\d+)"
)

# speaker = L1
speaker_regex = re.compile(
    r"speaker = (.*)"
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
        if os.path.isfile(path_project_config):
            with open(path_project_config, "r", encoding="utf-8") as infile:
                project_config = json.load(infile)
        else:
            project_config = {}
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

    # new: for Klang project admin table
    @staticmethod
    def get_project_transcribers(project_name: str):
        sample2transcribers = {}
        transcriber2samples = {}
        samples = KlangService.get_project_samples(project_name)
        for sample in samples:
            transcribers = [t['user'] for t in TranscriptionService.load_transcriptions(project_name, sample)]
            for t in transcribers:
                transcriber2samples[t] = transcriber2samples.get(t,[]) + [sample]
            sample2transcribers[sample] = transcribers
        users = {transcriber:UserService.get_by_username(transcriber) for transcriber in transcriber2samples}
        transcribers = [
            {
            'name':transcriber, 
            'id':users[transcriber].id, 
            'auth provider':'Google' if int(users[transcriber].auth_provider)==3 else "GitHub", 
            'first name':users[transcriber].first_name, 
            'family name':users[transcriber].family_name, 
            'last seen':str(users[transcriber].last_seen.date()), 
            'Klang projects':', '.join(samples)
            } 
                for transcriber,samples in transcriber2samples.items()]
        tableColumns = [{'name':k, 'label':k, 'field':k} for k in transcribers[0]]
        return [sample2transcribers, transcribers, tableColumns]
    
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
        os.makedirs(KlangService.get_path_data(), mode=0o777, exist_ok=True)
        return os.listdir(KlangService.get_path_data())

    @staticmethod
    def get_project_samples(project_name: str):
        """returns all klang project naturally sorted"""
        files = os.listdir(KlangService.get_path_project_samples(project_name))
        splitfiles = sorted([[ (int(c) if c.isdigit() else c) for c in re.split(r'(\d+)', f) ] for f in files])
        return [''.join([str(c) for c in sf]) for sf in splitfiles]

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
        speaker_info = 0 
        for line in sentence.split("\n"):
            if line:
                if line.startswith("#"):
                    m = speaker_regex.search(line)
                    if m:
                        speaker_info = m.group(1)
                else:
                    m = align_begin_and_end_regex.search(line)
                    audio_token = [m.group(1), m.group(2), m.group(3)]
                    audio_tokens.append(audio_token)

        return audio_tokens, speaker_info

    @staticmethod
    def compute_conll_audio_tokens(conll: str):
        sentences = KlangService.conll_to_sentences(conll)
        conll_audio_tokens = []
        conll_speakers = []
        for sentence in sentences:
            audio_tokens, speaker_info = KlangService.sentence_to_audio_tokens(sentence)
            conll_audio_tokens.append(audio_tokens)
            conll_speakers.append(speaker_info)
        return conll_audio_tokens, conll_speakers


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