from os import path, stat
from typing import Dict, List, Tuple


def healthy():
    return True


class ConllProcessor:
    def __init__(self):
        return

    @staticmethod
    def get_document(path_conll: str) -> str:
        with open(path_conll, "r", encoding="utf-8") as infile:
            conll_document = infile.read()
        return conll_document

    @staticmethod
    def document_to_sentences(conll_document: str) -> List[str]:
        conll_sentences = conll_document.split("\n\n")
        return conll_sentences

    @staticmethod
    def split_meta_and_tree(conll_sentence: str) -> Tuple[str, str]:
        sentence_conll_meta, sentence_conll_tree = "", ""
        for line in conll_sentence:
            if line.startswith("#"):
                sentence_conll_meta += line
            else:
                sentence_conll_tree += line

        return sentence_conll_meta, sentence_conll_tree

    @staticmethod
    def sentence_conll_to_sentence_json(sentence_conll: str):
        sentence_json = SentenceJson()
        sentence_json.from_sentence_conll(sentence_conll)
        return sentence_json

    @staticmethod
    def sentences_conll_to_sentences_json(sentences_conll):
        sentences_json = []
        for sentence_conll in sentences_conll:
            sentence_json = ConllProcessor.sentence_conll_to_sentence_json(
                sentence_conll
            )
            sentences_json.append(sentence_json)

        return sentences_json

    @staticmethod
    def conll_document_to_sentences_json(conll_document: str):
        conll_sentences = ConllProcessor.document_to_sentences(conll_document)
        sentences_json = ConllProcessor.sentences_conll_to_sentences_json(
            conll_sentences
        )
        return sentences_json

    @staticmethod
    def conll_document_path_to_sentences_json(conll_document_path):
        conll_document = ConllProcessor.get_document(conll_document_path)
        sentences_json = ConllProcessor.conll_document_to_sentences_json(conll_document)
        return sentences_json


class TokenProcessor:
    @staticmethod
    def conll_mapping_to_dict_mapping(conll_mapping: str) -> Dict[str, str]:
        dict_mapping = {}

        if not conll_mapping == "_":

            key_value_couples = conll_mapping.split("|")

            for key_value in key_value_couples:
                key, value = StringProcessor.process_key_value(key_value, "=")
                if key and value:
                    dict_mapping[key] = value
                else:
                    print(f"<CONLLUP> parsing error : '{conll_mapping}' is not a valid conll_mapping")

        return dict_mapping

    @staticmethod
    def dict_mapping_to_conll_mapping(dict_mapping: Dict[str, str]) -> str:
        if dict_mapping == {}:
            conll_mapping = "_"

        else:
            key_value_couples = []
            for key, value in dict_mapping.items():
                key_value_couple = f"{key}={value}"
                key_value_couples.append(key_value_couple)

            conll_mapping = "|".join(key_value_couples)

        return conll_mapping

    @staticmethod
    def extract_token_id(splitted_token_conll: List[str]) -> str:
        id = splitted_token_conll[0]
        return id

    @staticmethod
    def extract_token_form(splitted_token_conll: List[str]) -> str:
        form = splitted_token_conll[1]
        return form

    @staticmethod
    def extract_token_lemma(splitted_token_conll: List[str]) -> str:
        lemma = splitted_token_conll[2]
        return lemma

    @staticmethod
    def extract_token_upos(splitted_token_conll: List[str]) -> str:
        upos = splitted_token_conll[3]
        return upos

    @staticmethod
    def extract_token_xpos(splitted_token_conll: List[str]) -> str:
        xpos = splitted_token_conll[4]
        return xpos

    @staticmethod
    def extract_token_feats(splitted_token_conll: List[str]) -> Dict[str, str]:
        feats = TokenProcessor.conll_mapping_to_dict_mapping(splitted_token_conll[5])
        return feats

    @staticmethod
    def extract_token_head(splitted_token_conll: List[str]) -> str:
        head = splitted_token_conll[6]
        return head

    @staticmethod
    def extract_token_deprel(splitted_token_conll: List[str]) -> str:
        deprel = splitted_token_conll[7]
        return deprel

    @staticmethod
    def extract_token_deps(splitted_token_conll: List[str]) -> Dict[str, str]:
        deps = TokenProcessor.conll_mapping_to_dict_mapping(splitted_token_conll[8])
        return deps

    @staticmethod
    def extract_token_miscs(splitted_token_conll: List[str]) -> Dict[str, str]:
        miscs = TokenProcessor.conll_mapping_to_dict_mapping(splitted_token_conll[9])
        return miscs


class TokenJson(dict):
    def __init__(self):
        return

    def from_token_conll(self, token_conll: str) -> None:
        stripped_token_conll = token_conll.strip("# ").rstrip("\n")
        splitted_token_conll = stripped_token_conll.split("\t")
        self["id"] = TokenProcessor.extract_token_id(splitted_token_conll)
        self["form"] = TokenProcessor.extract_token_form(splitted_token_conll)
        self["lemma"] = TokenProcessor.extract_token_lemma(splitted_token_conll)
        self["upos"] = TokenProcessor.extract_token_upos(splitted_token_conll)
        self["xpos"] = TokenProcessor.extract_token_xpos(splitted_token_conll)
        self["feats"] = TokenProcessor.extract_token_feats(splitted_token_conll)
        self["head"] = TokenProcessor.extract_token_head(splitted_token_conll)
        self["deprel"] = TokenProcessor.extract_token_deprel(splitted_token_conll)
        self["deps"] = TokenProcessor.extract_token_deps(splitted_token_conll)
        self["misc"] = TokenProcessor.extract_token_miscs(splitted_token_conll)

    def from_token_json(self, token_json) -> None:
        for key, value in token_json.items():
            self[key] = value

    def to_token_conll(self) -> str:
        token_line_list: List[str] = [
            self["id"],
            self["form"],
            self["lemma"],
            self["upos"],
            self["xpos"],
            TokenProcessor.dict_mapping_to_conll_mapping(self["feats"]),
            self["head"],
            self["deprel"],
            TokenProcessor.dict_mapping_to_conll_mapping(self["deps"]),
            TokenProcessor.dict_mapping_to_conll_mapping(self["misc"]),
        ]

        return "\t".join(token_line_list) + "\n"


class MetaJson(dict):
    def __init__(self):
        return

    def add_meta(self, line):
        stripped_line = line.strip("# ").rstrip("\n")
        meta_key, meta_value = StringProcessor.process_key_value(stripped_line, " = ")
        if meta_key and meta_value:
            self[meta_key] = meta_value
        else:
            print(f"<CONLLUP> parsing error : '{stripped_line}' is not a valid meta")

    def from_meta_conll(self, meta_conll: str) -> None:
        for line in meta_conll.split("\n"):
            if not line:
                continue

            stripped_line = line.strip("# ").rstrip("\n")
            splitted_line = stripped_line.split(" = ")
            meta = splitted_line[0]
            value = splitted_line[1]
            self[meta] = value

    def from_meta_json(self, meta_json) -> None:
        for key, value in meta_json.items():
            self[key] = value

    def to_meta_conll(self) -> str:
        ordered_meta_key = sorted(list(self.keys()))

        key_value_couples: List[str] = []
        for meta_key in ordered_meta_key:
            meta_value = self[meta_key]
            key_value_couple = f"# {meta_key} = {meta_value}"
            key_value_couples.append(key_value_couple)

        meta_conll = "\n".join(key_value_couples)
        return meta_conll


class TreeJson(dict):
    def __init__(self):
        return

    def add_token(self, token_conll: str) -> None:
        token_json = TokenJson()
        token_json.from_token_conll(token_conll)
        token_id = int(token_json["id"])
        self[token_id] = token_json

    def from_tree_json(self, tree_json) -> None:
        for token_id, token_json in tree_json.items():
            token_json = TokenJson()
            token_json.from_token_json(token_json)
            self[token_id] = token_json

    def to_tree_conll(self) -> str:
        token_conlls = []
        for token_id, token_json in self.items():
            token_conll: str = token_json.to_token_conll()
            token_conlls.append(token_conll)

        tree_conll = "\n".join(token_conlls)
        return tree_conll


class SentenceJson(dict):
    def __init__(self):
        self["meta"] = MetaJson()
        self["tree"] = TreeJson()

    def from_sentence_json(self, sentence_json) -> None:
        self["meta"].from_meta_json(sentence_json["meta"])
        self["tree"].from_tree_json(sentence_json["tree"])

    def from_sentence_conll(self, sentence_conll: str):
        for line in sentence_conll.split("\n"):
            if not line:
                continue
            if line.startswith("#"):
                self["meta"].add_meta(line)
            else:
                self["tree"].add_token(line)

    def to_sentence_conll(self) -> str:
        meta_conll: str = self["meta"].to_meta_conll()
        tree_conll: str = self["tree"].to_tree_conll()

        sentence_conll = f"{meta_conll}\n{tree_conll}\n"
        return sentence_conll


class StringProcessor:
    @staticmethod
    def process_key_value(key_value_string: str, seperator: str) -> Tuple[str, str]:
        if seperator not in key_value_string:
            return ("", "")
        else:
            key, value = key_value_string.split(seperator)
            return key, value
