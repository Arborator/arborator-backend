import json

from flask import current_app

from ..models.models import SampleExerciseLevel
from ..repository import samples_dao, project_dao
from ..utils.grew_utils import grew_request
from ..utils.conll3 import conll3



def get_project_samples(project_name):
    project = project_dao.find_by_name(project_name)
    reply = grew_request('getSamples', current_app, data = {'project_id': project_name} )
    js = json.loads(reply)
    data = js.get("data")
    samples=[]
    if data:
        for sa in data:
            sample={'sample_name':sa['name'], 'sentences':sa['number_sentences'], 'number_trees':sa['number_trees'], 'tokens':sa['number_tokens'], 'treesFrom':sa['users'], "roles":{}}
            sample["roles"] = project_dao.get_sample_roles(project.id, sa['name'])
            
            sample_exercise_level = samples_dao.get_sample_exercise_level(sa['name'], project.id)
            if sample_exercise_level:
                sample["exerciseLevel"] = sample_exercise_level.exercise_level.code
            else:
                sample["exerciseLevel"] = 4
                
            samples.append(sample)
    return samples


def get_sample_exercise_level(sample_name, project_id) -> int:
    # return the integer of the exercise level
    sample_exercise_level = samples_dao.get_sample_exercise_level(sample_name, project_id)
    if sample_exercise_level:
        return sample_exercise_level.exercise_level.code
    else:
        return 4


def create_or_update_sample_exercise_level(sample_name, project_id, new_exercise_level):
    sample_exercise_level = samples_dao.get_sample_exercise_level(sample_name, project_id)
    if not sample_exercise_level:
        sample_exercise_level = samples_dao.create_sample_exercise_level(sample_name, project_id, new_exercise_level)
    else:
        sample_exercise_level = samples_dao.update_sample_exercise_level(sample_name, project_id, new_exercise_level)
    
    return sample_exercise_level



################################################################################
##################                                       #######################
##################            Tree functions             #######################
##################                                       #######################
################################################################################


def samples2trees(samples, sample_name):
    ''' transforms a list of samples into a trees object '''
    trees={}
    for sentId, users in samples.items():	
        for user_id, conll in users.items():
            tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = {"sample_name":sample_name ,"sentence":tree.sentence(), "conlls": {}, "matches":{}}
            trees[sentId]["conlls"][user_id] = conll
    return trees


def samples2trees_with_restrictions(samples, sample_name, current_user, project_name):
    ''' transforms a list of samples into a trees object and restrict it to user trees and default tree(s) '''
    trees={}
    p = project_dao.find_by_name(project_name)
    default_user_trees_ids = [dut.username for dut in project_dao.find_default_user_trees(p.id)]

    default_usernames = list()
    default_usernames = default_user_trees_ids
    # if len(default_user_trees_ids) > 0: default_usernames = user_dao.find_username_by_ids(default_user_trees_ids)
    if current_user.username not in default_usernames: default_usernames.append(current_user.username)
    for sentId, users in samples.items():	
        filtered_users = { username: users[username] for username in default_usernames  if username in users}
        for user_id, conll in filtered_users.items():
            tree = conll3.conll2tree(conll)
            if sentId not in trees: trees[sentId] = {"sample_name":sample_name ,"sentence":tree.sentence(), "conlls": {}, "matches":{}}
            trees[sentId]["conlls"][user_id] = conll
    return trees

BASE_TREE = "base_tree"

def samples2trees_exercise_mode(trees_on_grew, sample_name, current_user, project_name):
    ''' transforms a list of samples into a trees object and restrict it to user trees and default tree(s) '''
    trees_processed = {}
    usernames = ["teacher", current_user.username]

    for tree_id, tree_users in trees_on_grew.items():
        trees_processed[tree_id] = {"sample_name":sample_name ,"sentence": "", "conlls": {}, "matches":{}}
        for username, tree in tree_users.items():
            if username in usernames:
                trees_processed[tree_id]["conlls"][username] = tree
                # add the sentence to the dict
                # TODO : put this script on frontend and not in backend (add a conllu -> sentence in javascript)
                # if tree:
                if trees_processed[tree_id]["sentence"] == "":
                    trees_processed[tree_id]["sentence"] = conll3.conll2tree(tree).sentence()
                    
                    ### add the base tree (emptied conllu) ###
                    empty_conllu = conll3.emptyConllu(tree)
                    base_conllu = conll3.changeMetaField(empty_conllu, "user_id", BASE_TREE)
                    trees_processed[tree_id]["conlls"][BASE_TREE] = base_conllu
        
        
        if current_user.username not in trees_processed[tree_id]["conlls"]:
            empty_conllu = conll3.emptyConllu(tree)
            user_empty_conllu = conll3.changeMetaField(empty_conllu, "user_id", current_user.username)
            trees_processed[tree_id]["conlls"][current_user.username] = user_empty_conllu
    return trees_processed