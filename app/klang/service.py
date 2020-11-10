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
        audio_tokens = []
        for line in sentence_string.split("\n"):
            if line:
                if not line.startswith("#"):
                    m = align_begin_and_end_regex.search(line)
                    audio_tokens += [(m.group(1), int(m.group(2)), int(m.group(3)))]
        
        return audio_tokens
