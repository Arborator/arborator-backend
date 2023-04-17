from typing import List, Literal, Dict
from conllup.conllup import sentenceConllToJson, readConlluFile, writeConlluFile
import os
import re

from datetime import datetime

from app import db
from app.config import MAX_TOKENS, Config
from app.user.model import User
from app.utils.grew_utils import GrewService
from flask import abort
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from .model import SampleExerciseLevel, SampleRole

BASE_TREE = "base_tree"


class SampleUploadService:
    @staticmethod
    def upload(
        fileobject: FileStorage,
        project_name: str,
        reextensions=None,
        existing_samples=[],
        users_ids_convertor={},
    ):		
        if reextensions == None:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")
        filename = secure_filename(fileobject.filename)
        sample_name = reextensions.sub("", filename)
        path_file = os.path.join(Config.UPLOAD_FOLDER, filename)
        print('upload\n', path_file)
        fileobject.save(path_file)
        nrtoks = convert_users_ids(path_file, users_ids_convertor)
        add_or_keep_timestamps(path_file)
        if nrtoks>Config.MAX_TOKENS:
            abort(406, "Too big: Sample files on ArboratorGrew should have less than {max} tokens<br>Your file {fn} has {nrtoks} tokens. Split your file into smaller samples.".format(max=Config.MAX_TOKENS, fn=fileobject.filename, nrtoks=nrtoks))
        if sample_name not in existing_samples:
            GrewService.create_sample(project_name, sample_name)

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)




class SampleRoleService:
    @staticmethod
    def create(new_attrs):
        new_sample_role = SampleRole(**new_attrs)
        db.session.add(new_sample_role)
        db.session.commit()
        return new_sample_role

    @staticmethod
    def get_one(
        project_id: int,
        sample_name: str,
        user_id: int,
        role: int,
    ):
        """Get one specific user role """
        role = (
            db.session.query(SampleRole)
            .filter(SampleRole.user_id == user_id)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .filter(SampleRole.role == role)
            .first()
        )

    @staticmethod
    def delete_one(
        project_id: int,
        sample_name: str,
        user_id: int,
        role: int,
    ):
        """Delete one specific user role """
        role = (
            db.session.query(SampleRole)
            .filter(SampleRole.user_id == user_id)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .filter(SampleRole.role == role)
            .first()
        )
        if not role:
            return []
        db.session.delete(role)
        db.session.commit()
        return [(project_id, sample_name, user_id, role)]

    @staticmethod
    def get_by_sample_name(project_id: int, sample_name: str):
        """Get a dict of annotators and validators for a given sample"""
        roles = {}
        for r, label in SampleRole.ROLES:
            role = (
                db.session.query(User, SampleRole)
                .filter(User.id == SampleRole.user_id)
                .filter(SampleRole.project_id == project_id)
                .filter(SampleRole.sample_name == sample_name)
                .filter(SampleRole.role == r)
                .all()
            )
            roles[label] = [{"key": a.username, "value": a.username} for a, b in role]

        return roles

    @staticmethod
    def delete_by_sample_name(project_id: int, sample_name: str):
        """Delete all access of a sample. Used after a sample deletion was asked by the user
        ... perform on grew server."""
        roles = (
            db.session.query(SampleRole)
            .filter(SampleRole.project_id == project_id)
            .filter(SampleRole.sample_name == sample_name)
            .all()
        )
        for role in roles:
            db.session.delete(role)
        db.session.commit()

        return

    # def get_annotators_by_sample_id(project_id: int, sample_id: int) -> List[str]:
    #     return


class SampleExerciseLevelService:
    @staticmethod
    def create(new_attrs) -> SampleExerciseLevel:
        new_sample_access_level = SampleExerciseLevel(**new_attrs)
        db.session.add(new_sample_access_level)
        db.session.commit()
        return new_sample_access_level

    @staticmethod
    def update(sample_exercise_level: SampleExerciseLevel, changes):
        sample_exercise_level.update(changes)
        db.session.commit()
        return sample_exercise_level

    @staticmethod
    def get_by_sample_name(project_id: int, sample_name: str) -> SampleExerciseLevel:
        sample_exercise_level = SampleExerciseLevel.query.filter_by(
            sample_name=sample_name, project_id=project_id
        ).first()
        return sample_exercise_level

    @staticmethod
    def delete_by_sample_name(project_id: int, sample_name: str):
        """Delete all access of a sample. Used after a sample deletion was asked by the user
        ... perform on grew server."""
        roles = (
            db.session.query(SampleExerciseLevel)
            .filter(SampleExerciseLevel.project_id == project_id)
            .filter(SampleExerciseLevel.sample_name == sample_name)
            .all()
        )
        for role in roles:
            db.session.delete(role)
        db.session.commit()

        return



class SampleEvaluationService:
    @staticmethod
    def evaluate_sample(sample_conlls):
        corrects = {}
        submitted = {}
        total = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}
        for sentence_id, sentence_conlls in sample_conlls.items():
            teacher_conll = sentence_conlls.get("teacher")
            if teacher_conll:
                teacher_sentence_json = sentenceConllToJson(
                    teacher_conll
                )
                teacher_tree = teacher_sentence_json["treeJson"]['nodesJson']

                basetree_conll = sentence_conlls.get(BASE_TREE)
                if basetree_conll:
                    basetree_sentence_json = (
                        sentenceConllToJson(basetree_conll)
                    )
                    basetree_tree = basetree_sentence_json["treeJson"]['nodesJson']
                else:
                    basetree_tree = {}

                for token_id in teacher_tree.keys():
                    teacher_token = teacher_tree.get(token_id)
                    if teacher_token == None:
                        continue
                    basetree_token = basetree_tree.get(token_id, {})
                    for label in ["UPOS", "HEAD", "DEPREL"]:
                        if (
                            teacher_token[label] != "_"
                            and basetree_token.get(label) != teacher_token[label]
                        ):
                            total[label] += 1
            else:
                continue

            for user_id, user_conll in sentence_conlls.items():

                if user_id != "teacher":
                    if not corrects.get(user_id):
                        corrects[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}
                    if not submitted.get(user_id):
                        submitted[user_id] = {"UPOS": 0, "DEPREL": 0, "HEAD": 0}

                    user_sentence_json = sentenceConllToJson(
                        user_conll
                    )
                    user_tree = user_sentence_json["treeJson"]["nodesJson"]

                    for token_id in user_tree.keys():
                        teacher_token = teacher_tree.get(token_id)
                        if teacher_token == None:
                            continue

                        user_token = user_tree.get(token_id)
                        basetree_token = basetree_tree.get(token_id, {})

                        for label in ["UPOS", "HEAD", "DEPREL"]:
                            if (
                                teacher_token[label] != "_"
                                and basetree_token.get(label) != teacher_token[label]
                            ):
                                if user_token[label] != "_":
                                    submitted[user_id][label] += 1
                                corrects[user_id][label] += (
                                    teacher_token[label] == user_token[label]
                                )
        GRADE = 100
        evaluations = {}
        for user_id in corrects.keys():
            evaluations[user_id] = {}
            for label in ["UPOS", "HEAD", "DEPREL"]:
                if total[label] == 0:
                    score = 0
                else:
                    score = corrects[user_id][label] / total[label]

                score_on_twenty = score * GRADE
                rounded_score = int(score_on_twenty)
                evaluations[user_id][f"{label}_total"] = total[label]
                evaluations[user_id][f"{label}_submitted"] = submitted[user_id][label]
                evaluations[user_id][f"{label}_correct"] = corrects[user_id][label]
                evaluations[user_id][f"{label}_grade_on_{GRADE}"] = rounded_score

        return evaluations

    @staticmethod
    def evaluations_json_to_tsv(evaluations):
        if evaluations == {}:
            # noone works on these trees
            return ""

        list_usernames = list(evaluations.keys())
        first_username = list(evaluations.keys())[0]
        columns = list(evaluations[first_username].keys())

        evaluations_tsv = "\t".join(["usernames"] + list_usernames)

        for label in columns:
            user_tsv_line_list = [label]
            for username in list_usernames:
                user_tsv_line_list.append(str(evaluations[username][label]))
            user_tsv_line_string = "\t".join(user_tsv_line_list)
            evaluations_tsv += "\n" + user_tsv_line_string
        return evaluations_tsv


#
#
#############    Helpers Function    #############
#
#
def read_conll_from_disk(path_file: str) -> str:
    try: 
        with open(path_file, "r") as infile:
            conll_string = infile.read()
    except:
        abort(415)
    return conll_string  
   


def split_conll_string_to_conlls_list(conll_string) -> List[str]:
    conlls_strings = conll_string.split("\n\n")
    return conlls_strings


def write_conll_on_disk(path_file: str, conll_string: str) -> None:
    conll_string.rstrip()
    conll_string += "\n\n"
    with open(path_file, "w") as outfile:
        outfile.write(conll_string)
    return


def convert_users_ids(path_file, users_ids_convertor):
    nrtoks = 0
    conll_string = read_conll_from_disk(path_file)
    conlls_strings = split_conll_string_to_conlls_list(conll_string)
    conlls_string_modified = []
    for conll_string in conlls_strings:
        if conll_string == "":
            continue
        conll_lines_modified = []
        user_id = "default"

        for line in conll_string.rstrip().split("\n"):
            if line:
                if "# user_id = " in line:
                    user_id = line.split("# user_id = ")[-1]
                else:
                    conll_lines_modified.append(line)
                    if line[0]!='#':
                        nrtoks+=1

        user_id_converted = users_ids_convertor[user_id]
        conll_lines_modified = ["# user_id = {}".format(user_id_converted)] + conll_lines_modified
        conlls_string_modified.append("\n".join(conll_lines_modified))

    new_file_string = "\n\n".join(conlls_string_modified)
    write_conll_on_disk(path_file, new_file_string)
    return nrtoks


def readConlluFileWrapper(path_file: str, keepEmptyTrees: bool = False):
    """ read a conllu file and return a list of sentences """
    try:
        sentences_json = readConlluFile(path_file, keepEmptyTrees=keepEmptyTrees)
        return sentences_json
    except Exception as e:
        abort(406, str(e))

def writeConlluFileWrapper(path_file: str, sentences_json: List[Dict]):
    """ write a conllu file from a list of sentences """
    try:
        writeConlluFile(path_file, sentences_json, overwrite=True)
    except Exception as e:
        abort(406, str(e))


def add_or_keep_timestamps(path_file: str, when: Literal["now", "long_ago"] = "now"):
    """ adds a timestamp on the tree if there is not one """
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    timestamp_str = str(datetime.timestamp(datetime.now()) * 1000)
    if when == "long_ago":
        timestamp_str = 0
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["timestamp"] = sentence_json["metaJson"].get("timestamp", timestamp_str)

    writeConlluFileWrapper(path_file, sentences_json)


def add_or_replace_userid(path_file: str, new_user_id: str):
    """ adds a userid on the tree or replace it if already has one """
    sentences_json = readConlluFileWrapper(path_file, keepEmptyTrees=True)
    for sentence_json in sentences_json:
        sentence_json["metaJson"]["user_id"] = new_user_id

    writeConlluFileWrapper(path_file, sentences_json)


