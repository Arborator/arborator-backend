from conllup.conllup import sentenceConllToJson
from conllup.processing import constructTextFromTreeJson, emptySentenceConllu, changeMetaFieldInSentenceConllu

from app.utils.grew_utils import GrewService
BASE_TREE = "base_tree"
VALIDATED = "validated"

class TreeService:

    @staticmethod
    def samples2trees(samples, sample_name):
        """ transforms a list of samples into a trees object """
        trees = {}
        for sent_id, users in samples.items():
            for user_id, conll in users.items():
                sentenceJson = sentenceConllToJson(conll)
                sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
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
    def extract_trees_from_sample(sample, sample_name):
        """ transforms a samples into a trees object """
        trees = {}
        for sent_id, users in sample.items():
            for user_id, conll in users.items():
                sentenceJson = sentenceConllToJson(conll)
                sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
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
    def samples2trees_with_restrictions(samples, sample_name, current_user):
        """ transforms a list of samples into a trees object and restrict it to user trees and default tree(s) """
        trees = {}
    
        default_user_trees_ids = []
        default_usernames = list()
        default_usernames = default_user_trees_ids

        if current_user.username not in default_usernames:
            default_usernames.append(current_user.username)
        for sent_id, users in samples.items():
            filtered_users = {
                username: users[username]
                for username in default_usernames
                if username in users
            }
            for user_id, conll in filtered_users.items():
                sentenceJson = sentenceConllToJson(conll)
                sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
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
    def samples2trees_exercise_mode(trees_on_grew, sample_name, current_user, project_name):
        """ transforms a list of samples into a trees object and restrict it to user trees and default tree(s) """
        trees_processed = {}
        usernames = ["teacher", current_user.username]

        for sent_id, tree_users in trees_on_grew.items():
            trees_processed[sent_id] = {
                "sample_name": sample_name,
                "sentence": "",
                "sent_id": sent_id,
                "conlls": {},
                "matches": {},
            }
            for username, conll in tree_users.items():
                if username in usernames:
                    trees_processed[sent_id]["conlls"][username] = conll
                    # add the sentence to the dict
                    # TODO : put this script on frontend and not in backend (add a conllu -> sentence in javascript)
                    # if tree:
                    if trees_processed[sent_id]["sentence"] == "":
                        sentenceJson = sentenceConllToJson(conll)
                        sentence_text = constructTextFromTreeJson(sentenceJson["treeJson"])
                        trees_processed[sent_id]["sentence"] = sentence_text

                        ### add the base tree (emptied conllu) ###
                        empty_conllu = emptySentenceConllu(conll)
                        base_conllu = changeMetaFieldInSentenceConllu(empty_conllu, "user_id", BASE_TREE)
                        trees_processed[sent_id]["conlls"][BASE_TREE] = base_conllu

            if current_user.username not in trees_processed[sent_id]["conlls"]:
                empty_conllu = emptySentenceConllu(conll)
                user_empty_conllu = changeMetaFieldInSentenceConllu(
                    empty_conllu, "user_id", current_user.username
                )
                trees_processed[sent_id]["conlls"][
                    current_user.username
                ] = user_empty_conllu
        return trees_processed

    @staticmethod
    def get_user_trees(project_name, sample_name, username):
        
        user_trees_sent_ids = []
        grew_sample_trees = GrewService.get_sample_trees(project_name, sample_name)
        sample_trees = TreeService.extract_trees_from_sample(grew_sample_trees, sample_name)
        for sent_id, trees in sample_trees.items():
            if username in trees['conlls']: 
                user_trees_sent_ids.append(sent_id)
            
            return user_trees_sent_ids

