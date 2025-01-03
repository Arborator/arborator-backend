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
    """this class contains all methods that deal with trees"""

    @staticmethod
    def check_cycle(conll): 
        """check if there is a cycle in the graph

        Args:
            conll (str): user tree

        Returns:
            cycle_nodes (List[List[str]]): list of cycles nodes
        """
        sentence_json = sentenceConllToJson(conll)
        nodes_json = sentence_json['treeJson']['nodesJson']
        
        nodes_children_list = {}
        for index in nodes_json:
            if index not in nodes_children_list.keys():
                nodes_children_list[index] = []
            token_head = str(nodes_json[index]['HEAD'])
            if token_head not in nodes_children_list.keys():
                nodes_children_list[token_head] = [index]
            else:
                nodes_children_list[token_head].append(index)
        print(nodes_children_list)

        # check if there is a cycle in the tree using recursive dfs
        def dfs_recursive(first_node, visited, stack, path):
            visited.add(first_node)
            stack.add(first_node)
            path.append(first_node)
            
            for child in nodes_children_list[first_node]:
                if child not in visited:
                    if dfs_recursive(child, visited, stack, path):
                        return True
                elif child in stack:
                    path.append(child)
                    return True
            stack.remove(first_node)
            path.pop()
            return False
        
        visited = set()
        stack = set()
        cycle_nodes = []

        for node in nodes_children_list:
            if node not in visited:
                path = []
                if dfs_recursive(node, visited, stack, path):
                    cycle_start_index = cycle_nodes.index(path[-1]) if path[-1] in cycle_nodes else 0
                    cycle_nodes.append(path[cycle_start_index:])

        return cycle_nodes
                     
    @staticmethod
    def samples_to_trees(sample_trees, sample_name):
        """ 
            transforms a list of samples into a trees object  
        Args: 
            samples_trees (grew_sample_trees) 
            sample_name (str)
        Returns: 
            {"sent_id": {"sample_name": "", "sentence": "", "sent_id": "", "conlls": {"user_id1": ""}, "matches": {}}}
        """
        trees = {}
        for sent_id, users in sample_trees.items():
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
        """
            for blind annotation mode we add base tree in trees object 
        Args:
            trees (trees_object): {"sent_id": {"sample_name": "", "sentence": "", "sent_id": "", "conlls": {"user_id1": ""}, "matches": {}}}
        Returns:
            trees (trees_object)     
        """
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
        """Add user tree in blind annotation mode all users start with empty base tree

        Args:
            trees (tree_object)
            username (str)

        Returns:
           trees
        """
        for sent_trees in trees.values():
            sent_conlls = sent_trees["conlls"]
            list_users = list(sent_conlls.keys())
            if username not in list_users:
                sent_conlls[username] = sent_conlls[BASE_TREE]
        return trees

    @staticmethod
    def restrict_trees(trees, restricted_users):
        """Remove all users trees that are ont in restricted_users list

        Args:
            trees (trees_object)
            restricted_users (List[str]): list of username

        Returns:
            trees
        """
        for sent_trees in trees.values():
            sent_conlls = sent_trees["conlls"]
            for user_id in list(sent_conlls.keys()):
                if user_id not in restricted_users:
                    del sent_conlls[user_id]
        return trees
    
    @staticmethod
    def update_sentence_trees_with_new_sent_id(project_name, sample_name, old_sent_id, new_sent_id):
        """
            This function is used when we update sent_id of sentence, 
            since saveGraph uses sent_id so we can't use it in our case 
            so we use saveConll instead and use change all the trees of a sentence

        Args:
            project_name (str)
            sample_name (str)
            old_sent_id (str)
            new_sent_id (str)
        """
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
    """this class used for tree segmentation feature"""
    @staticmethod
    def insert_new_sentences(project_name: str, sample_name, sent_id: str, inserted_sentences):
        """Insert new sentences in specific position, this function is used for sentence split and merge

        Args:
            project_name (str)
            sample_name (str)
            sent_id (str)
            inserted_sentences (sentenceJson)
        """
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
    """This class deals with trees validation features"""
    @staticmethod
    def extract_ud_languages():
        """extract ud languages list"""
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
        """Parse validation result message

        Args:
            message (str)

        Returns:
            error_messages ({"sent_id": "message" })
        """
        error_messages = {}
        messages = message.split("---")
        if len(messages) > 1:
            for message in messages:
                if re.findall(r"Sent (.*?) Line", message):
                    sent_id = re.findall(r"Sent (.*?) Line", message)[0]
                    error_messages[sent_id] = message
        return error_messages