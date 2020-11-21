import os

from app.test.fixtures import app, db  # noqa

from .service import ConllService

folder_name = "data_test"
file_name = "John_Doe"


def test_get_path_data():
    path_data = ConllService.get_path_data()
    print("KK path_data", path_data)
    assert os.path.isdir(path_data)


def test_get_path_conll():
    path_conll = ConllService.get_path_conll(file_name)
    assert os.path.isfile(path_conll)


def test_read_conll():
    path_conll = ConllService.get_path_conll(file_name)
    conll_string = ConllService.read_conll(path_conll)
    assert type(conll_string) == str


def test_get_all():
    conlls = ConllService.get_all_name()
    assert conlls == ["John_Doe"]


def test_get_by_name():
    path_conll = ConllService.get_path_conll(file_name)
    conll_string = ConllService.read_conll(path_conll)
    assert conll_string == ConllService.get_by_name(file_name)


def test_seperate_conll_sentences():
    conll_string = "# sent_id = test_sentence_1\n1\ttest_token\ntest_lemma\ntest_upos\n\n# sent_id = test_sentence_2\n1\ttest_token\ntest_lemma\ntest_upos\n\n"
    sentences = ConllService.seperate_conll_sentences(conll_string)
    assert len(sentences) == 2


def test_sentence_to_audio_tokens():
    sentence = "# sent_id = test_sentence_1\n1\tdonc\tdonc\t_\t_\t_\t_\t_\t_\tAlignBegin=0|AlignEnd=454"
    audio_tokens = ConllService.sentence_to_audio_tokens(sentence)
    assert audio_tokens[0][0] == "donc"
    assert audio_tokens[0][1] == "0"
    assert audio_tokens[0][2] == "454"
    ## these three following lines are an example of what we should get 
    # assert audio_tokens[0]["token"] == "donc"
    # assert audio_tokens[0]["alignBegin"] == 0
    # assert audio_tokens[0]["alignEnd"] == 454

# when we will have new structure, we can use this
# def test_process_sentences_audio_token():
#     sentences_audio_token = ConllService.process_sentences_audio_token(file_name)
#     assert sentences_audio_token == [{
#         1: {"token": "it", "alignBegin": 100, "alignEnd": 500},
#         2: {"token": "is", "alignBegin": 600, "alignEnd": 1000}
#     }]