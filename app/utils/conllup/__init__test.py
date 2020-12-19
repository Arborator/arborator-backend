import json
import os

from . import (
    ConllProcessor,
    MetaJson,
    SentenceJson, StringProcessor,
    TokenJson,
    TokenProcessor,
    TreeJson,
    healthy,
)

BASEDIR = os.path.dirname(os.path.abspath(__file__))
path_conll_test = os.path.join(BASEDIR, "test.conllu")

sentence_conll_test = """# sent_id = test
# meta_key = meta_value
1\tit\t_\t_\t_\t_\t_\t_\t_\t_
2\tis\t_\t_\t_\t_\t_\t_\t_\t_
3\ta\t_\t_\t_\t_\t_\t_\t_\t_
4\ttest\t_\t_\t_\t_\t_\t_\t_\t_
5\t.\t_\t_\t_\t_\t_\t_\t_\t_
"""
sentence_conll_meta_test = """# sent_id = test
# meta_key = meta_value
"""

sentence_conll_meta_test_sorted = """# meta_key = meta_value
# sent_id = test"""

conll_mapping_test = "key1=value1|key2=value2"

token_conll_test = """1\tform\tlemma\tupos\txpos\tfeat_key=feat_value\t0\tdeprel\tdep_key=dep_value\tmisc_key=misc_value
"""

splitted_token_conll_test = [
    "id",
    "form",
    "lemma",
    "upos",
    "xpos",
    "feat_key=feat_value",
    "head",
    "deprel",
    "dep_key=dep_value",
    "misc_key=misc_value",
]


splitted_empty_token_conll_test = [
    "id",
    "_",
    "_",
    "_",
    "_",
    "_",
    "_",
    "_",
    "_",
    "_",
]

sentence_json_test_folder_name = "sentence_test.json"
sentence_json_test_folder_path = os.path.join(BASEDIR, sentence_json_test_folder_name)
with open(sentence_json_test_folder_path, "r", encoding="utf-8") as infile:
    sentence_json_test = json.loads(infile.read())


def test_healthy():
    assert healthy()


def test_conll_processor():
    conll_processor = ConllProcessor()
    assert conll_processor


def test_get_document():
    conll_document = ConllProcessor.get_document(path_conll_test)
    assert conll_document
    assert "sent_id = test" in conll_document


def test_document_to_sentences():
    conll_document = ConllProcessor.get_document(path_conll_test)
    conll_sentences = ConllProcessor.document_to_sentences(conll_document)
    assert conll_sentences
    assert "sent_id = test" in conll_sentences[0]
    assert len(conll_sentences) == 2


def test_split_meta_and_tree():
    sentence_conll_meta, sentence_conll_tree = ConllProcessor.split_meta_and_tree(
        sentence_conll_test
    )
    assert sentence_conll_meta, sentence_conll_tree


def test_create_instance_meta_json():
    meta_json = MetaJson()
    assert meta_json == {}


def test_meta_json_from_meta_conll():
    meta_json = MetaJson()
    meta_json.from_meta_conll(sentence_conll_meta_test)
    assert meta_json["sent_id"] == "test"
    assert meta_json["meta_key"] == "meta_value"
    assert len(meta_json.keys()) == 2


def test_meta_json_to_meta_conll():
    meta_json = MetaJson()
    meta_json.from_meta_conll(sentence_conll_meta_test)

    meta_conll = meta_json.to_meta_conll()
    assert meta_conll == sentence_conll_meta_test_sorted


def test_create_instance_token_json():
    token_json = TokenJson()
    assert token_json == {}


def test_dict_mapping_to_conll_mapping():
    dict_mapping = {"key1": "value1", "key2": "value2"}
    conll_mapping = TokenProcessor.dict_mapping_to_conll_mapping(dict_mapping)
    assert conll_mapping == conll_mapping_test


def test_conll_mapping_to_dict_mapping():
    dict_mapping = TokenProcessor.conll_mapping_to_dict_mapping(conll_mapping_test)
    assert dict_mapping == {"key1": "value1", "key2": "value2"}

    dict_empty_mapping = TokenProcessor.conll_mapping_to_dict_mapping("_")
    assert dict_empty_mapping == {}


def test_extract_token_id():
    token_id = TokenProcessor.extract_token_id(splitted_token_conll_test)
    assert token_id == "id"


def test_extract_token_form():
    token_form = TokenProcessor.extract_token_form(splitted_token_conll_test)
    assert token_form == "form"


def test_extract_token_lemma():
    token_lemma = TokenProcessor.extract_token_lemma(splitted_token_conll_test)
    assert token_lemma == "lemma"


def test_extract_token_upos():
    token_upos = TokenProcessor.extract_token_upos(splitted_token_conll_test)
    assert token_upos == "upos"


def test_extract_token_xpos():
    token_xpos = TokenProcessor.extract_token_xpos(splitted_token_conll_test)
    assert token_xpos == "xpos"


def test_extract_token_feats():
    token_feats = TokenProcessor.extract_token_feats(splitted_token_conll_test)
    assert token_feats == {"feat_key": "feat_value"}

    token_empty_feats = TokenProcessor.extract_token_feats(
        splitted_empty_token_conll_test
    )
    assert token_empty_feats == {}


def test_extract_token_head():
    token_head = TokenProcessor.extract_token_head(splitted_token_conll_test)
    assert token_head == "head"


def test_extract_token_deprel():
    token_deprel = TokenProcessor.extract_token_deprel(splitted_token_conll_test)
    assert token_deprel == "deprel"


def test_extract_token_deps():
    token_deps = TokenProcessor.extract_token_deps(splitted_token_conll_test)
    assert token_deps == {"dep_key": "dep_value"}

    token_token_deps = TokenProcessor.extract_token_feats(
        splitted_empty_token_conll_test
    )
    assert token_token_deps == {}


def test_extract_token_miscs():
    token_miscs = TokenProcessor.extract_token_miscs(splitted_token_conll_test)
    assert token_miscs == {"misc_key": "misc_value"}


def test_token_json_from_token_conll():
    token_json = TokenJson()
    token_json.from_token_conll(token_conll_test)
    assert token_json["id"] == "1"
    assert token_json["form"] == "form"
    assert token_json["lemma"] == "lemma"
    assert token_json["upos"] == "upos"
    assert token_json["xpos"] == "xpos"
    assert token_json["feats"] == {"feat_key": "feat_value"}
    assert token_json["head"] == "0"
    assert token_json["deprel"] == "deprel"
    assert token_json["deps"] == {"dep_key": "dep_value"}
    assert token_json["misc"] == {"misc_key": "misc_value"}


def test_token_json_to_token_conll():
    token_json = TokenJson()
    token_json.from_token_conll(token_conll_test)

    token_conll = token_json.to_token_conll()
    assert token_conll == token_conll_test


def test_tree_json_add_token():
    tree_json = TreeJson()
    tree_json.add_token(token_conll_test)
    assert tree_json[1]["id"] == "1"


def test_tree_json_to_tree_token():
    tree_json = TreeJson()
    tree_json.add_token(token_conll_test)

    tree_conll = tree_json.to_tree_conll()

    assert tree_conll == token_conll_test


def test_create_instance_sentence_json():
    sentence_json = SentenceJson()
    assert sentence_json == {"meta": {}, "tree": {}}


def test_sentence_json_from_sentence_conll():
    sentence_json = SentenceJson()
    sentence_json.from_sentence_conll(sentence_conll_test)
    assert sentence_json["meta"]["sent_id"] == "test"


def test_sentence_json_from_sentence_json():
    sentence_json = SentenceJson()
    sentence_json.from_sentence_json(sentence_json_test)
    assert sentence_json["meta"]["sent_id"] == "test"
    assert hasattr(sentence_json["meta"], "from_meta_json")
    assert hasattr(sentence_json["tree"], "from_tree_json")


def test_sentence_json_to_sentence_conll():
    sentence_json = SentenceJson()
    sentence_json.from_sentence_conll(sentence_conll_test)

    sentence_conll = sentence_json.to_sentence_conll()
    assert sentence_conll


def test_conll_document_to_sentences_json():
    sentences_json = ConllProcessor.conll_document_path_to_sentences_json(
        path_conll_test
    )
    assert sentences_json
    assert len(sentences_json) == 2

def test_process_key_value():
    assert StringProcessor.process_key_value("a=b", seperator="=") == ("a","b")
    assert StringProcessor.process_key_value("a = b", seperator=" = ") == ("a","b")
    assert StringProcessor.process_key_value("a=b", seperator="==") == ("","")
