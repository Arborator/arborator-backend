import json 
import time
import jwt
import requests
import re

# from ..models.models import *
from flask import current_app, abort
from app.config import Config # prod
from flask_login import current_user
# from ..utils.conll3 import conll3
# from ..utils.grew_utils import grew_request, upload_project
# from ..repository import project_dao, user_dao, robot_dao
# from ..services import robot_service
# from werkzeug import secure_filename
# from datetime import datetime
# from flask import abort
# from decimal import Decimal

# # tokens for github api


def app_headers():
    """
    header for communication with github api
    """
    time_since_epoch_in_seconds = int(time.time())
    payload = {
      # issued at time
      'iat': time_since_epoch_in_seconds,
      # JWT expiration time (10 minute maximum)
      'exp': time_since_epoch_in_seconds + (9 * 60),
      # GitHub App's identifier
      'iss': current_app.config['APP_ID'] #arborator-grew-id
    }

    actual_jwt = jwt.encode(payload, current_app.config['PKEY'], algorithm='RS256')

    headers = {"Authorization": "Bearer {}".format(actual_jwt.decode()),
               "Accept": "application/vnd.github.machine-man-preview+json"}
    return headers

def get_installation_id():
    resp = requests.get('https://api.github.com/app/installations', headers=app_headers())
    installations = json.loads(resp.content.decode())
    # print("installations", installations)
    if resp.status_code == 404:
        abort(404)
    elif resp.status_code == 200:
        installation_id = [account["id"] for account in installations if account["account"]["login"] == current_user.username]
        if installation_id:
            return installation_id[0]
        else:
            return False

def get_token():
    app_id = current_app.config['APP_ID']
    installation_id = get_installation_id()
    # print("== app id", app_id, "== installation_id", installation_id)
    resp = requests.post('https://api.github.com/installations/{}/access_tokens'.format(installation_id),
                     headers=app_headers())
    if resp.status_code != 201:
        abort(resp.status_code)
    else:
        # print('Code: ', resp.status_code)
        # print('Content: ', resp.content.decode())
        token = json.loads(resp.content.decode()).get("token")
        return token

def base_header():
    token = get_token()
    headers = {"Authorization": "token {}".format(token),
           "Accept": "application/vnd.github.machine-man-preview+json"}
    return headers


def get_user_repository(username):
    # get a user
    resp = requests.get('https://api.github.com/installation/repositories', headers=base_header())
    if resp.status_code == 404:
        abort(404)
    elif resp.status_code == 200:
        repos = json.loads(resp.content.decode())["repositories"]
        filtered_repos = []
        for rep in repos:
            owner = rep["owner"]
            if owner["login"] == username:
                filtered_repos.append(rep["full_name"])
        return filtered_repos[0] # users should only give us access to one repository ?

# def exists_project_repository(username, project_name):
#     user_repo = get_user_repository(username)
#     resp = requests.get('https://api.github.com/repos/{}/contents/{}'.format(user_repo, project_name), headers=base_header())
#     if resp.status_code == 200:
#         return True
#     else:
#         print(resp.status_code, "\n", resp.content.decode())
#         return False

def exists_sample(username, project_name, sample_name):
    user_repo = get_user_repository(username)
    resp = requests.get('https://api.github.com/repos/{}/contents/{}/{}'.format(user_repo, project_name, sample_name), headers=base_header())
    return resp

def make_commit(user_repo, data, project_name, sample_name):
    # print('https://api.github.com/repos/{}/contents/{}'.format(user_repo, path))
    resp = requests.put('https://api.github.com/repos/{}/contents/{}/{}'.format(user_repo, project_name, sample_name), headers=base_header(), json=data)
    return resp

def get_sample(username, project_name, sample_name):
    user_repo = get_user_repository(username)
    resp = requests.get('https://api.github.com/repos/{}/contents/{}/{}'.format(user_repo, project_name, sample_name), headers=base_header())
    return resp

def get_all_users(username, project_name, sample_name):
    user_repo = get_user_repository(username)
    resp = requests.get('https://api.github.com/repos/{}/contents/{}'.format(user_repo, project_name), headers=base_header())
    if resp.status_code == 200:
        users = []
        data = json.loads(resp.content.decode())
        for sample in data:
            name = sample["name"]
            match = re.search(sample_name+"_(.+)$", name).groups()
            if match:
                user = match[0]
                if user != "last":
                    users.append(user)
        return users
    else:
        abort(404)