from app.utils.conllup import ConllProcessor
import io
import json
import os
import re
import time
import zipfile
from datetime import datetime

from app import db
from app.config import Config
from app.user.model import User
from app.utils.conll3 import conllFile2trees, trees2conllFile
from app.utils.grew_utils import GrewService, grew_request
from flask import abort, current_app
from sqlalchemy.sql.operators import startswith_op
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
        fileobject.save(path_file)

        convert_users_ids(path_file, users_ids_convertor)
        add_or_keep_timestamps(path_file)
        # tmpfile = add_or_keep_timestamps(path_file)

        if sample_name not in existing_samples:
            GrewService.create_sample(project_name, sample_name)

        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)


# TODO : refactor this
class SampleExportService:
    @staticmethod
    def servSampleTrees(samples):
        """ get samples in form of json trees """
        trees = {}
        for sentId, users in samples.items():
            for user_id, conll in users.items():
                # tree = conll3.ConllProcessor.sentence_conll_to_sentence_json(conll)
                if sentId not in trees:
                    trees[sentId] = {"conlls": {}}
                trees[sentId]["conlls"][user_id] = conll
        return trees

    @staticmethod
    def sampletree2contentfile(tree):
        if isinstance(tree, str):
            tree = json.loads(tree)
        usertrees = dict()
        for sentId in tree.keys():
            for user, conll in tree[sentId]["conlls"].items():
                if user not in usertrees:
                    usertrees[user] = list()
                usertrees[user].append(conll)
        for user, content in usertrees.items():
            usertrees[user] = "\n".join(usertrees[user])
        return usertrees

    @staticmethod
    def get_last_user(tree):
        timestamps = [(user, get_timestamp(conll)) for (user, conll) in tree.items()]
        if len(timestamps) == 1:
            last = timestamps[0][0]
        else:
            # print(timestamps)
            last = sorted(timestamps, key=lambda x: x[1])[-1][0]
            # print(last)
        return last

    @staticmethod
    def contentfiles2zip(sample_names, sampletrees):
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w") as zf:
            for sample_name, sample in zip(sample_names, sampletrees):
                for fuser, filecontent in sample.items():
                    data = zipfile.ZipInfo("{}.{}.conllu".format(sample_name, fuser))
                    data.date_time = time.localtime(time.time())[:6]
                    data.compress_type = zipfile.ZIP_DEFLATED
                    zf.writestr(data, filecontent)
        memory_file.seek(0)
        return memory_file


# TODO : refactor this
def get_timestamp(conll):
    t = re.search("# timestamp = (\d+(?:\.\d+)?)\n", conll).groups()
    if t:
        return t[0]
    else:
        return False


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


from app.utils.conll3 import conll2tree


class SampleEvaluationService:
    @staticmethod
    def evaluate_sample(sample_conlls):
        corrects = {}
        submitted = {}
        total = {"upos": 0, "deprel": 0, "head": 0}
        for sentence_id, sentence_conlls in sample_conlls.items():
            teacher_conll = sentence_conlls.get("teacher")
            if teacher_conll:
                teacher_sentence_json = ConllProcessor.sentence_conll_to_sentence_json(
                    teacher_conll
                )
                teacher_tree = teacher_sentence_json["tree"]

                basetree_conll = sentence_conlls.get(BASE_TREE)
                if basetree_conll:
                    basetree_sentence_json = (
                        ConllProcessor.sentence_conll_to_sentence_json(basetree_conll)
                    )
                    basetree_tree = basetree_sentence_json["tree"]
                else:
                    basetree_tree = {}

                for token_id in teacher_tree.keys():
                    teacher_token = teacher_tree.get(token_id)
                    basetree_token = basetree_tree.get(token_id, {})
                    for label in ["upos", "head", "deprel"]:
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
                        corrects[user_id] = {"upos": 0, "deprel": 0, "head": 0}
                    if not submitted.get(user_id):
                        submitted[user_id] = {"upos": 0, "deprel": 0, "head": 0}

                    user_sentence_json = ConllProcessor.sentence_conll_to_sentence_json(
                        user_conll
                    )
                    user_tree = user_sentence_json["tree"]

                    for token_id in user_tree.keys():
                        teacher_token = teacher_tree.get(token_id)
                        user_token = user_tree.get(token_id)
                        basetree_token = basetree_tree.get(token_id, {})

                        for label in ["upos", "head", "deprel"]:
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
            for label in ["upos", "deprel", "head"]:
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


def convert_users_ids(path_file, users_ids_convertor):
    # with open(path_file, "r", encoding="utf-8") as infile, open(path_file + "out", "w", encoding="utf-8") as outfile:
    #     for line in infile.readlines():
    #         if line.startswith("# user_id"):
    #             old_user_id = line.strip("# user_id = ").rstrip("\n")
    #             new_user_id = users_ids_convertor[old_user_id]
    #             line = "# user_id = " + new_user_id + "\n"

    #         outfile.write(line)
    # os.rename(path_file + "out", path_file)
    trees = conllFile2trees(path_file)

    for tree in trees:
        tree_current_user_id = tree.sentencefeatures.get("user_id", "default")
        tree.sentencefeatures["user_id"] = users_ids_convertor[tree_current_user_id]

    trees2conllFile(trees, path_file)
    return

    # if tree_current_user_id in users_ids_convertor.keys():
    #     tree.sentencefeatures[]


def add_or_keep_timestamps(path_file: str):
    """ adds a timestamp on the tree if there is not one """
    # TODO : do this more efficiently
    # path_tmp_file = os.path.join(Config.UPLOAD_FOLDER, "tmp.conllu")
    trees = conllFile2trees(path_file)
    for t in trees:
        if not t.sentencefeatures.get("timestamp"):
            now = datetime.now()
            # int  millisecondes
            timestamp = datetime.timestamp(now) * 1000
            timestamp = round(timestamp)
            t.sentencefeatures["timestamp"] = str(timestamp)

    trees2conllFile(trees, path_file)
    return path_file
    # trees2conllFile(trees, path_tmp_file)
    # return path_tmp_file
