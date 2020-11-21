import os
import re
from typing import List
from sqlalchemy import exc
import sys
import json
from flask import abort
import time

from app import klang_config, db
from .model import Transcription
from app.user.model import User
from flask_login import current_user

align_begin_and_end_regex = re.compile(
    r"^\d+\t(.+?)\t.*AlignBegin=(\d+).*AlignEnd=(\d+)"
)


class ConllService:
    @staticmethod
    def get_path_data():
        path_data = klang_config.path
        return path_data

    @staticmethod
    def get_path_conll(file_name_suffix):
        file_name = file_name_suffix + ".intervals.conll"
        path_data = ConllService.get_path_data()
        path_conll = os.path.join(path_data, file_name_suffix, file_name)
        return path_conll

    @staticmethod
    def read_conll(path_conll):
        with open(path_conll, "r", encoding="utf-8") as infile:
            conll = infile.read()
        return conll

    @staticmethod
    def get_all_name():
        path_data = ConllService.get_path_data()
        conlls = os.listdir(path_data)
        return conlls

    @staticmethod
    def get_by_name(conll_name):
        path_conll = ConllService.get_path_conll(conll_name)
        conll_string = ConllService.read_conll(path_conll)
        return conll_string

    @staticmethod
    def seperate_conll_sentences(conll_string: str) -> List[str]:
        return list(filter(lambda x: x != "", conll_string.split("\n\n")))

    @staticmethod
    def sentence_to_audio_tokens(sentence_string: str):
        audio_tokens = []
        for line in sentence_string.split("\n"):
            if line:
                if not line.startswith("#"):
                    m = align_begin_and_end_regex.search(line)
                    audio_token = [m.group(1), m.group(2), m.group(3)]
                    audio_tokens.append(audio_token)

        
        return audio_tokens

    @staticmethod
    def process_sentences_audio_token(conll_name: str):
        conll_string = ConllService.get_by_name(conll_name)
        sentences_string = ConllService.seperate_conll_sentences(conll_string)
        sentences_audio_token = []
        for sentence_string in sentences_string:
          audio_tokens = ConllService.sentence_to_audio_tokens(sentence_string)
          sentences_audio_token.append(audio_tokens)
        return sentences_audio_token

    @staticmethod
    def get_transcription(user_name, conll_name):
        result = {
            'transcription': [],
        }
        try:
            record = Transcription.query.filter_by(
                    user = user_name, 
                    mp3 = conll_name).one()
            trans = json.loads(record.transcription)
            result['transcription'] = trans
            result['sound'] = record.sound
            result['story'] = record.story
            result['accent'] = record.accent
            result['monodia'] = record.monodia
            result['title'] = record.title
            pass
        except exc.SQLAlchemyError:
            print(sys.exc_info()[0])
            pass
        return result

    @staticmethod
    def get_users_list(is_admin):
        users = []
        if is_admin == 'true':
            users = [x.username for x in User.query.all()]
        elif current_user.is_authenticated:
            users = [current_user.username]
        return users
    
    @staticmethod
    def save_transcription(conll_name, transcription, sound, story, accent, monodia, title):
        user_name = current_user.username
        try:
            Transcription.query.filter_by(
                user = user_name, 
                mp3 = conll_name
            ).delete(synchronize_session = False)
            trans_str = json.dumps(transcription)
            record = Transcription(
                user = user_name, 
                mp3 = conll_name, 
                transcription = trans_str,
                sound = sound,
                story = story,
                accent = accent,
                monodia = monodia,
                title = title
            )
            db.session.add(record)
            db.session.commit()
            pass
        except:
            print(sys.exc_info()[0])
            db.session.rollback()
            abort(400)
            pass
