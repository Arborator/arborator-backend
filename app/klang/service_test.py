from .service import ConllService
from app.test.fixtures import app, db  # noqa
import os

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
    conlls = ConllService.get_all()
    assert conlls == ["John_Doe"]

# # def test_get_by_name():
# #     # conll = ConllService.get_by_name("John_Doe")
# #     conll_string = ConllService.get_by_name(file_name)
# #     path_conll = ConllService.get_path_conll(folder_name, file_name)
# #     conll_string = ConllService.read_conll(path_conll)
# #     assert type(conll_string) == str