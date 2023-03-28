import os
import requests
import base64
import json
from flask import abort
from app import db
from typing import List
from app.config import MAX_TOKENS, Config
from .model import GithubRepository, GithubCommitStatus
from app.projects.service import ProjectService
from app.samples.service import convert_users_ids, add_or_keep_timestamps, read_conll_from_disk
from app.utils.grew_utils import GrewService


class GithubSynchronizationService:
    @staticmethod
    def get_github_synchronized_repository(user_id, project_id):
        github_repository: GithubRepository = GithubRepository.query.filter(GithubRepository.user_id == user_id).filter(GithubRepository.project_id == project_id).first()
        if github_repository: 
            return github_repository.repository_name
        else: 
            return ''
    

    @staticmethod
    def synchronize_github_repository(user_id, project_id, repository_name):

        github_repository ={
            "project_id": project_id,
            "user_id": user_id, 
            "repository_name": repository_name,
        }
        synchronized_github_repository = GithubRepository(**github_repository)
        db.session.add(synchronized_github_repository)
        db.session.commit()
    

    @staticmethod
    def delete_synchronization(user_id, project_id):
        github_repository: GithubRepository = GithubRepository.query.filter(GithubRepository.user_id == user_id).filter(GithubRepository.project_id == project_id).first()
        db.session.delete(github_repository)
        db.session.commit()


class GithubWorkflowService:
    @staticmethod
    def import_files_from_github(access_token, full_name, project_name, username):
        repository_files = GithubService.get_repository_files(access_token, full_name)
        GithubService.create_new_branch_arborator(access_token, full_name)
        for file in repository_files:
            sample_name, path_file = GithubWorkflowService.create_file_from_github_file_content(file.get('name'), file.get('download_url'))
            user_ids = GithubWorkflowService.preprocess_file(path_file,username)
            GithubWorkflowService.create_sample(sample_name, path_file, project_name, user_ids)
            GithubCommitStatusService.create(ProjectService.get_by_name(project_name).id, sample_name)

    
    @staticmethod 
    def create_file_from_github_file_content(file_name, download_url):
        sample_name = file_name.split(".")[0]
        raw_content = requests.get(download_url)
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        file = open(path_file, "w")
        file.write(raw_content.text)

        return sample_name, path_file
    

    @staticmethod
    def preprocess_file(path_file, username):
        user_ids = {}
        user_ids["default"] = username
        file = read_conll_from_disk(path_file)
        for line in file.rstrip().split("\n"):
            if "# user_id = " in line:
                user_id = line.split("# user_id = ")[-1]
                user_ids[user_id] =user_id
        return user_ids
        

    @staticmethod
    def create_sample(sample_name, path_file, project_name, users_ids):
        tokens_number = convert_users_ids(path_file, users_ids)
        add_or_keep_timestamps(path_file)
        if tokens_number > MAX_TOKENS:
            abort(406, "Too big: Sample files on ArboratorGrew should have less than {max} tokens.".format(max=MAX_TOKENS))
        GrewService.create_sample(project_name, sample_name)
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)

    
    @staticmethod
    def commit_changes(access_token, full_name, updated_samples, project_name, username, message):
        parent = GithubService.get_sha_base_tree(access_token, full_name, "arboratorgrew")
        tree = GithubService.create_tree(access_token,full_name, updated_samples, project_name, username, parent)
        sha = GithubService.create_commit(access_token, tree, parent, message, full_name)
        response =GithubService.update_sha(access_token, full_name, "arboratorgrew", sha)
        return response.json()


    @staticmethod 
    def update_file_content(content, sha, message, url, access_token):
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {'sha': sha, 'message': message, 'content': encoded_content}
        response = requests.put(url, headers = GithubService.base_header(access_token), data = json.dumps(data))
        return response
    

class GithubService: 
    @staticmethod    
    def base_header(access_token):
        return {"Authorization": "bearer " + access_token}
    

    @staticmethod
    def get_user_information(access_token):
        response = requests.get("https://api.github.com/user", headers = GithubService.base_header(access_token))
        data = response.json()
        return data
    

    @staticmethod
    def get_user_email(access_token) -> str:
        response = requests.get("https://api.github.com/user/emails", headers = GithubService.base_header(access_token))
        data = response.json()
        return data[0].get("email")
    
    
    @staticmethod    
    def get_repositories(access_token):
        repositories = []
        response = requests.get("https://api.github.com/user/repos", headers = GithubService.base_header(access_token))
        data = response.json()
        for repo in data:
            repository = {}
            repository["name"] = repo.get("full_name")
            repository["owner_name"] = repo.get("owner").get("login")
            repository["owner_avatar"] = repo.get("owner").get("avatar_url")
            repositories.append(repository)
        return repositories  
    
          
    @staticmethod    
    def get_repository_files(access_token, full_name):
        response = requests.get("https://api.github.com/repos/{}/contents".format(full_name), headers = GithubService.base_header(access_token))
        data = response.json()
        return data
    

    @staticmethod   
    def get_file_sha(access_token, full_name, file_path):
        response = requests.get("https://api.github.com/repos/{}/contents/{}".format(full_name, file_path), headers = GithubService.base_header(access_token))
        data = response.json()
        return data.get("sha")
    

    @staticmethod
    def get_default_branch(access_token, full_name):
        response = requests.get("https://api.github.com/repos/{}".format(full_name), headers = GithubService.base_header(access_token))
        data = response.json()
        return data.get("default_branch")
    
    
    @staticmethod
    def get_sha_base_tree(access_token, full_name, branch):
        response = requests.get("https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch), headers = GithubService.base_header(access_token))
        data = response.json()
        return data.get("object").get("sha")
    
    
    @staticmethod
    def get_sha_last_commit(access_token, full_name, branch):
        response = requests.get("https://api.github.com/repos/{}/commits/{}".format(full_name, branch), headers = GithubService.base_header(access_token))
        data = response.json()
        return data.get("sha")
    

    @staticmethod
    def create_blob_for_updated_file(access_token, full_name, content):
        data = {"content": content, "encoding": "utf-8"}
        response = requests.post("https://api.github.com/repos/{}/git/blobs".format(full_name), headers = GithubService.base_header(access_token), data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
    

    @staticmethod 
    def create_tree(access_token, full_name, updated_samples, project_name, username, base_tree):
        tree = []
        sample_names, sample_content_files = GrewService.get_samples_with_string_contents(project_name, updated_samples)
        for sample_name, sample in zip(sample_names,sample_content_files):
            content = sample.get(username)
            sha = GithubService.create_blob_for_updated_file(access_token, full_name, content)
            blob = {"path": sample_name+".conllu", "mode":"100644", "type":"blob", "sha": sha}
            tree.append(blob)
        data = {"tree": tree, "base_tree": base_tree}
        response = requests.post("https://api.github.com/repos/{}/git/trees".format(full_name), headers = GithubService.base_header(access_token), data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
        
    
    @staticmethod
    def create_commit(access_token, tree, parent, message, full_name):
        data = {"tree": tree, "parents": [parent], "message": message}
        response = requests.post("https://api.github.com/repos/{}/git/commits".format(full_name), headers = GithubService.base_header(access_token), data = json.dumps(data) )
        data = response.json()
        return data.get("sha")


    @staticmethod
    def update_sha(access_token, full_name, branch, sha):
        data = {"sha": sha}
        response = requests.patch("https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch), headers = GithubService.base_header(access_token),  data= json.dumps(data))
        return response
    

    @staticmethod
    def create_github_repository(access_token, data):
        response = requests.post("https://api.github.com/user/repos", headers = GithubService.base_header(access_token), data = json.dumps(data) )
        return response
    

    @staticmethod
    def create_new_branch_arborator(access_token, full_name):
        default_branch = GithubService.get_default_branch(access_token, full_name) 
        sha = GithubService.get_sha_base_tree(access_token, full_name, default_branch)
        data = {
            "ref": "refs/heads/arboratorgrew",
            "sha": sha
        }
        response = requests.post("https://api.github.com/repos/{}/git/refs".format(full_name), headers = GithubService.base_header(access_token), data = json.dumps(data))
        return response.json()

class GithubCommitStatusService:
    @staticmethod
    def create(project_id, sample_name):
        commit_status = {
            "sample_name": sample_name,
            "project_id": project_id,
            "changes_number": 0,
        }
        print(commit_status)
        github_commit_status = GithubCommitStatus(**commit_status)
        db.session.add(github_commit_status)
        db.session.commit()
        return github_commit_status

    @staticmethod
    def update(project_id, sample_name):
        github_commit_status: GithubCommitStatus = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.sample_name == sample_name).first()
        if github_commit_status: 
            github_commit_status.changes_number = github_commit_status.changes_number + 1
            db.session.commit()
    
    def get_modified_samples(project_id) -> List[str]:
        modified_samples = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.changes_number > 0)
        return [modified_sample.sample_name for modified_sample in modified_samples]
    

    def reset_samples(project_id, modified_samples):
        for sample_name in modified_samples:
            github_commit_status: GithubCommitStatus = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.sample_name == sample_name).first()
            github_commit_status.changes_number = 0
            db.session.commit()


          



