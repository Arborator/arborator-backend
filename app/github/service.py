import os
import requests
import base64
import json
import re 
from datetime import datetime

from flask import abort

from app import db
from typing import List
from app.config import MAX_TOKENS, Config
from .model import GithubRepository, GithubCommitStatus
from app.projects.service import ProjectService
import app.samples.service as SampleService
from app.utils.grew_utils import GrewService, grew_request , SampleExportService




extension = re.compile("^.*\.(conllu)$")

class GithubSynchronizationService:
    @staticmethod
    def get_github_synchronized_repository(project_id):
        github_repository: GithubRepository = GithubRepository.query.filter(GithubRepository.project_id == project_id).first()
        if github_repository: 
            return github_repository.repository_name , github_repository.base_sha
        else: 
            return '', ''
    

    @staticmethod
    def synchronize_github_repository(user_id, project_id, repository_name, sha):

        github_repository ={
            "project_id": project_id,
            "user_id": user_id, 
            "repository_name": repository_name,
            "base_sha": sha,
        }
        synchronized_github_repository = GithubRepository(**github_repository)
        db.session.add(synchronized_github_repository)
        db.session.commit()
    

    @staticmethod
    def update_base_sha(project_id, repository_name, sha):
        github_synchronized_repo: GithubRepository = GithubRepository.query.filter(GithubRepository.repository_name == repository_name).filter(GithubRepository.project_id == project_id).first()
        if github_synchronized_repo:
            github_synchronized_repo.base_sha = sha
            db.session.commit()
        

    @staticmethod
    def delete_synchronization(user_id, project_id):
        github_repository: GithubRepository = GithubRepository.query.filter(GithubRepository.user_id == user_id).filter(GithubRepository.project_id == project_id).first()
        db.session.delete(github_repository)
        db.session.commit()


class GithubWorkflowService:

    @staticmethod
    def import_files_from_github(access_token, full_name, project_name, username, branch):
        repository_files = GithubService.get_repository_files_from_specific_branch(access_token, full_name, branch)
        conll_files = [file for file in repository_files if extension.search(file.get('name'))]
        if not conll_files:
            abort(400, "No conll Files in this repository")
        for file in conll_files:
            GithubWorkflowService.create_sample_from_github_file(file.get("name"), file.get("download_url"), username, project_name)
        GithubService.create_new_branch_arborator(access_token, full_name, branch)

    
    @staticmethod 
    def create_file_from_github_file_content(file_name, download_url):
        sample_name = file_name.split(".conllu")[0]
        raw_content = requests.get(download_url)
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        file = open(path_file, "w")
        file.write(raw_content.text)

        return sample_name, path_file
    

    @staticmethod
    def preprocess_file(path_file, username):
        user_ids = {}
        user_ids["default"] = username
        file = SampleService.read_conll_from_disk(path_file)
        for line in file.rstrip().split("\n"):
            if "# user_id = " in line:
                user_id = line.split("# user_id = ")[-1]
                user_ids[user_id] =user_id
        return user_ids
        

    @staticmethod
    def create_sample(sample_name, path_file, project_name, users_ids):
        tokens_number = SampleService.convert_users_ids(path_file, users_ids)
        SampleService.add_or_keep_timestamps(path_file)
        if tokens_number > MAX_TOKENS:
            abort(406, "Too big: Sample files on ArboratorGrew should have less than {max} tokens.".format(max=MAX_TOKENS))
        GrewService.create_sample(project_name, sample_name)
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)

    
    @staticmethod
    def create_sample_from_github_file(file, download_url, username, project_name):
        sample_name, path_file = GithubWorkflowService.create_file_from_github_file_content(file, download_url)
        user_ids = GithubWorkflowService.preprocess_file(path_file,username)
        GithubWorkflowService.create_sample(sample_name, path_file, project_name, user_ids)
        GithubCommitStatusService.create(project_name, sample_name)


    @staticmethod
    def commit_changes(access_token, full_name, updated_samples, project_name, username, message):
        parent = GithubService.get_sha_base_tree(access_token, full_name, "arboratorgrew")
        tree = GithubService.create_tree(access_token,full_name, updated_samples, project_name, username, parent)
        sha = GithubService.create_commit(access_token, tree, parent, message, full_name)
        response =GithubService.update_sha(access_token, full_name, "arboratorgrew", sha)
        data = response.json()
        return data.get("object").get("sha")


    @staticmethod 
    def update_file_content(content, sha, message, url, access_token):
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {'sha': sha, 'message': message, 'content': encoded_content}
        response = requests.put(url, headers = GithubService.base_header(access_token), data = json.dumps(data))
        return response
    

    @staticmethod
    def check_pull(access_token, project_name):
        project = ProjectService.get_by_name(project_name)
        full_name, sha = GithubSynchronizationService.get_github_synchronized_repository(project.id)
        base_tree = GithubService.get_sha_base_tree(access_token, full_name, "arboratorgrew")
        return sha != base_tree


    @staticmethod 
    def pull_changes(access_token, project_name, username, full_name, base_tree):

        tree = GithubService.get_tree(access_token, full_name, base_tree)
        files = [file.get('path') for file in tree if extension.search(file.get('path'))]
        grew_samples = GrewService.get_samples(project_name)
        sample_names = [sa["name"] for sa in grew_samples]
        for path in files:
            file_content= GithubService.get_file_content_by_commit_sha(access_token,full_name, path, base_tree)
            sample_name = file_content.get("name").split(".conllu")[0]
            if sample_name not in sample_names:
                GithubWorkflowService.create_sample_from_github_file(file_content.get("name"), file_content.get("download_url"), username, project_name)
            else: 
                GithubWorkflowService.pull_change_existing_sample(project_name, sample_name,username, file_content.get("download_url"))
    

    @staticmethod
    def pull_change_existing_sample(project_name, sample_name, username, download_url):
        content = requests.get(download_url).text
        conlls_strings = SampleService.split_conll_string_to_conlls_list(content)
        reply = grew_request(
                "getConll",
                data={"project_id": project_name, "sample_id": sample_name},
            )
        sample_trees =SampleExportService.servSampleTrees(reply.get("data", {}))
        
        modified_sentences = []
        for conll in conlls_strings:
            for line in conll.rstrip().split("\n"):
                if "# sent_id = " in line:
                    sent_id = line.split("# sent_id = ")[-1] 
                    modified_sentences.append((sent_id, conll))
                    grew_request("saveGraph",
                    data={
                        "project_id": project_name,
                        "sample_id": sample_name,
                        "user_id": username,
                        "sent_id": sent_id,
                        "conll_graph": conll,
                    })
        for sentence in list(sample_trees.keys()):
            if not any (sentence in sent_id for modified_sentence in modified_sentences):
                grew_request("eraseGraph",
                    data={
                        "project_id": project_name,
                        "sample_id": sample_name,
                        "sent_id": sentence,
                        "user_id": username,
                    })        

           
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
    def list_branches_repository(access_token, full_name) -> List[str]:
        response = requests.get("https://api.github.com/repos/{}/branches".format(full_name), headers = GithubService.base_header(access_token)) 
        data = response.json()
        return [branch.get("name") for branch in data if "dependabot" not in branch.get("name")]


    @staticmethod    
    def get_repository_files_from_specific_branch(access_token, full_name, branch):
        response = requests.get("https://api.github.com/repos/{}/contents/?ref={}".format(full_name, branch), headers = GithubService.base_header(access_token))
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
        try:
            return data.get("object").get("sha")
        except:
            abort(400, "The Github repository doesn't exist anymore") 
           
        
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
    def create_new_branch_arborator(access_token, full_name, default_branch):
        sha = GithubService.get_sha_base_tree(access_token, full_name, default_branch)
        data = {
            "ref": "refs/heads/arboratorgrew",
            "sha": sha
        }
        response = requests.post("https://api.github.com/repos/{}/git/refs".format(full_name), headers = GithubService.base_header(access_token), data = json.dumps(data))
        return response.json()
    

    @staticmethod
    def get_tree(access_token, full_name, base_tree):
        response = requests.get("https://api.github.com/repos/{}/git/trees/{}".format(full_name, base_tree), headers = GithubService.base_header(access_token))
        data = response.json()
        return data.get("tree")
    

    @staticmethod
    def get_file_content_by_commit_sha(access_token, full_name, file_path, sha):
        response = requests.get("https://api.github.com/repos/{}/contents/{}?ref={}".format(full_name, file_path, sha), headers = GithubService.base_header(access_token))
        data = response.json()
        return data
    

class GithubCommitStatusService:
    @staticmethod
    def create(project_name, sample_name):
        project = ProjectService.get_by_name(project_name)
        commit_status = {
            "sample_name": sample_name,
            "project_id": project.id,
            "changes_number": 0,
        }
        github_commit_status = GithubCommitStatus(**commit_status)
        db.session.add(github_commit_status)
        db.session.commit()
        return github_commit_status


    @staticmethod
    def update(project_name, sample_name):
        project = ProjectService.get_by_name(project_name)
        github_commit_status: GithubCommitStatus = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project.id).filter(GithubCommitStatus.sample_name == sample_name).first()
        if github_commit_status: 
            github_commit_status.changes_number = github_commit_status.changes_number + 1
            db.session.commit()
    

    @staticmethod
    def get_modified_samples(project_id) -> List[str]:
        modified_samples = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.changes_number > 0)
        return [modified_sample.sample_name for modified_sample in modified_samples]
    

    @staticmethod
    def get_changes_number(project_id):
        modified_samples = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.changes_number > 0)
        return sum(modified_sample.changes_number for modified_sample in modified_samples)
        
        
    @staticmethod
    def reset_samples(project_id, modified_samples):
        for sample_name in modified_samples:
            github_commit_status: GithubCommitStatus = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project_id).filter(GithubCommitStatus.sample_name == sample_name).first()
            github_commit_status.changes_number = 0
            db.session.commit()
    
