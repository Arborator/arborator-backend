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
from app.utils.grew_utils import grew_request
from flask import current_app
from sqlalchemy.sql.operators import startswith_op
from werkzeug.utils import secure_filename

from .model import SampleExerciseLevel, SampleRole


class SampleUploadService:
    @staticmethod
    def upload(
        fileobject,
        project_name,
        import_user,
        reextensions=None,
        existing_samples=[],
    ):
        if reextensions == None:
            reextensions = re.compile(r"\.(conll(u|\d+)?|txt|tsv|csv)$")

        filename = secure_filename(fileobject.filename)
        sample_name = reextensions.sub("", filename)
        fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

        if sample_name not in existing_samples:
            # create a new sample in the grew project
            print("========== [newSample]")
            reply = grew_request(
                "newSample",
                current_app,
                data={"project_id": project_name, "sample_id": sample_name},
            )
            print("reply = ", reply)

        else:
            print("/!\ sample already exists")

        tmpfile = add_or_keep_timestamps(os.path.join(Config.UPLOAD_FOLDER, filename))

        with open(tmpfile, "rb") as inf:
            print("========== [saveConll]")
            if import_user:
                reply = grew_request(
                    "saveConll",
                    current_app,
                    data={
                        "project_id": project_name,
                        "sample_id": sample_name,
                        "user_id": import_user,
                    },
                    files={"conll_file": inf},
                )
            else:  # if no import_user has been provided, it should be in the conll metadata
                reply = grew_request(
                    "saveConll",
                    current_app,
                    data={"project_id": project_name, "sample_id": sample_name},
                    files={"conll_file": inf},
                )

        print("REPLY S+TATIUUUSS", reply)
        if reply.get("status") == "OK":
            return 200, sample_name + " saved successfully on Grew"
        else:
            mes = reply.get("data", {}).get("message", "")
            # error because reply.get('message',{}) is a string
            error_message = reply.get("message", {}).get("Conllx_error:")
            error_sent_id = (
                reply.get("message", {}).get("Conllx_error:").get("sent_id", "")
            )
            if not mes:
                mes = "unknown problem"
            li = reply.get("data", {}).get("line", "")
            if li:
                li = " line " + str(li)
            else:
                li = ""
            return 400, sample_name + " caused a problem: " + mes + li
            # abort(400)


# TODO : refactor this
class SampleExportService:
    @staticmethod
    def servSampleTrees(samples):
        """ get samples in form of json trees """
        trees = {}
        for sentId, users in samples.items():
            for user_id, conll in users.items():
                # tree = conll3.conll2tree(conll)
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
            print("KK role", role)
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


#
#
#############    Helpers Function    #############
#
#


def add_or_keep_timestamps(conll_file):
    """ adds a timestamp on the tree if there is not one """
    # TODO : do this more efficiently
    tmpfile = os.path.join(Config.UPLOAD_FOLDER, "tmp.conllu")
    trees = conllFile2trees(conll_file)
    for t in trees:
        if t.sentencefeatures.get("timestamp"):
            continue
        else:
            now = datetime.now()
            # int  millisecondes
            timestamp = datetime.timestamp(now) * 1000
            timestamp = round(timestamp)
            t.sentencefeatures["timestamp"] = str(timestamp)
        # TODO check format of the conll while we're at it ?

    trees2conllFile(trees, tmpfile)
    return tmpfile
