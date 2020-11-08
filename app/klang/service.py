import os
from app import klang_config

class ConllService:
    @staticmethod
    def get_path_data():
        path_data = klang_config.path
        return path_data
    
    @staticmethod
    def get_path_conll(file_name_suffix):
        file_name = file_name_suffix + ".intervals.conll"
        path_data = ConllService.get_path_data()
        path_conll = os.path.join(path_data,file_name_suffix, file_name)
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

    # @staticmethod
    # def get_by_name(conll_name):
    #     with
    #     return True
