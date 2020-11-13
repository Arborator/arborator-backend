import os
import re
from typing import List

from app import klang_config

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
    def get_all():
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
        audio_tokens = {}
        for line in sentence_string.split("\n"):
            if line:
                if not line.startswith("#"):
                    m = align_begin_and_end_regex.search(line)
                    audio_token = {
                        "token": m.group(1),
                        "alignBegin": int(m.group(2)),
                        "alignEnd": int(m.group(3)),
                    }
                    audio_tokens[int(line.split("\t")[0])] = audio_token

        print(audio_tokens)
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
