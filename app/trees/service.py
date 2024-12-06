import os 
import requests
import re
from bs4 import BeautifulSoup

from conllup.conllup import sentenceConllToJson, sentenceJsonToConll
from conllup.processing import constructTextFromTreeJson, emptySentenceConllu

from app.config import Config
from app.utils.grew_utils import GrewService, grew_request
BASE_TREE = "base_tree"
VALIDATED = "validated"

class TreeService:
    
    @staticmethod
    def check_cycle(conll): 
        sentence_json = sentenceConllToJson(conll)
        nodes_json = sentence_json['treeJson']['nodesJson']
        
        nodes_children_list = {}
        for index in nodes_json:
            token_head = str(nodes_json[index]['HEAD'])
            if token_head not in nodes_children_list.keys():
                nodes_children_list[token_head] = [index]
            else:
                nodes_children_list[token_head].append(index)
        
        cycle_nodes = []        
        for node, list_children in nodes_children_list.items():
            for child in list_children:
                if child in nodes_children_list.keys() and node in nodes_children_list[child]:
                   cycle_nodes.append((child, node))
        
        return list(set(tuple(sorted(nodes_tuple)) for nodes_tuple in cycle_nodes))
                       
    @staticmethod
    def samples_to_trees(samples, sample_name):
        """ transforms a list of samples into a trees object """
        trees = {}
        for sent_id, users in samples.items():
            for user_id, conll in users.items():
                sentence_json = sentenceConllToJson(conll)
                if 'text' in sentence_json["metaJson"].keys():
                    sentence_text = sentence_json["metaJson"]["text"]
                else: 
                    sentence_text = constructTextFromTreeJson(sentence_json["treeJson"])
                if sent_id not in trees:
                    trees[sent_id] = {
                        "sample_name": sample_name,
                        "sentence": sentence_text,
                        "sent_id": sent_id,
                        "conlls": {},
                        "matches": {},
                    }
                trees[sent_id]["conlls"][user_id] = conll
        return trees

    @staticmethod
    def add_base_tree(trees):
        for sent_trees in trees.values():
            sent_conlls = sent_trees["conlls"]
            list_users = list(sent_conlls.keys())
            if BASE_TREE not in list_users:
                model_user = VALIDATED if VALIDATED in list_users else list_users[0]
                model_tree = sent_conlls[model_user]
                empty_conllu = emptySentenceConllu(model_tree)
                sent_conlls[BASE_TREE] = empty_conllu
        return trees
    
    @staticmethod
    def add_user_tree(trees, username):
        for sent_trees in trees.values():
            sent_conlls = sent_trees["conlls"]
            list_users = list(sent_conlls.keys())
            if username not in list_users:
                sent_conlls[username] = sent_conlls[BASE_TREE]
        return trees

    @staticmethod
    def restrict_trees(trees, restricted_users):
        for sent_trees in trees.values():
            sent_conlls = sent_trees["conlls"]
            for user_id in list(sent_conlls.keys()):
                if user_id not in restricted_users:
                    del sent_conlls[user_id]
        return trees
    
    @staticmethod
    def update_sentence_trees_with_new_sent_id(project_name, sample_name, old_sent_id, new_sent_id):
        
        response = grew_request('getConll', {
            "project_id": project_name,
            "sample_id": sample_name,
            "sent_id": old_sent_id
        })
        conlls = response.get("data")
    
        conll_inserted = ''
        for conll in conlls.values():
            sentence_json = sentenceConllToJson(conll)
            sentence_json['metaJson']['sent_id'] = new_sent_id
            conll_inserted += sentenceJsonToConll(sentence_json) + "\n\n"
            
        file_name = sample_name + "_new_sent_id.conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
    
        with open(path_file, "w") as file:
            file.write(conll_inserted)
            
        with open(path_file, "rb") as conll_file:
            GrewService.insert_conll(project_name, sample_name, old_sent_id, conll_file)  
            GrewService.erase_sentence(project_name, sample_name, old_sent_id)   
        
        os.remove(path_file)
                         
class TreeSegmentationService: 

    @staticmethod
    def insert_new_sentences(project_name: str, sample_name, sent_id: str, inserted_sentences):
        conll_to_insert = ''
        for sentences in inserted_sentences:
            for sentence_json in sentences.values():
                conll_to_insert += sentenceJsonToConll(sentence_json) + '\n\n'
            
        file_name = sample_name + "_inserted_conll.conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        
        with open(path_file, "w") as file:
            file.write(conll_to_insert)
        with open(path_file, "rb") as conll_file:
            GrewService.insert_conll(project_name, sample_name, sent_id, conll_file)
        
        os.remove(path_file)
            
            
class TreeValidationService:
    
    @staticmethod
    def extract_ud_languages():
        html_text = requests.get('https://quest.ms.mff.cuni.cz/udvalidator/cgi-bin/unidep/langspec/specify_feature.pl').text
        soup = BeautifulSoup(html_text, features="lxml")

        language_mapping = {}
        for a in soup.find_all('a'):
            if len(a.text) > 1:
                lang_code = a['href'].split('=')[1]
                language_mapping[a.text] = lang_code
        return language_mapping
    
    @staticmethod
    def parse_validation_results(message):
        error_messages = {}
        messages = message.split("---")
        if len(messages) > 1:
            for message in messages:
                if re.findall(r"Sent (.*?) Line", message):
                    sent_id = re.findall(r"Sent (.*?) Line", message)[0]
                    error_messages[sent_id] = message
        return error_messages