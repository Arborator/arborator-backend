import os
import requests
import base64
import json
import re 
import shutil
import zipfile
from typing import List

from flask import abort
from flask_login import current_user

from app import db
from app.config import Config
from app.projects.service import ProjectService
from app.utils.grew_utils import GrewService, grew_request , SampleExportService
from app.user.service import UserService
import app.samples.service as SampleService

from .model import GithubRepository, GithubCommitStatus


extension = re.compile("^.*\.(conllu)$")

class GithubSynchronizationService:

    @staticmethod
    def get_github_synchronized_repository(project_id):
        return GithubRepository.query.filter(GithubRepository.project_id == project_id).first()
    

    @staticmethod
    def synchronize_github_repository(user_id, project_id, repository_name, branch, sha):

        github_repository = {
            "project_id": project_id,
            "user_id": user_id, 
            "repository_name": repository_name,
            "branch": branch,
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
    def import_files_from_github(access_token, full_name, project_name, username, branch, branch_syn):

        repository_files = GithubService.get_repository_files_from_specific_branch(access_token, full_name, branch)
        conll_files = [file.get("name") for file in repository_files if extension.search(file.get('name'))]
        
        samples_names = [file.split(".conllu")[0] for file in conll_files]
        project_samples = GrewService.get_samples(project_name)
        existed_samples_names = [sample["name"] for sample in project_samples]
        not_intersected_samples = [sample_name for sample_name in existed_samples_names if sample_name not in samples_names]
        
        for sample_name in not_intersected_samples:
            GithubCommitStatusService.create(project_name, sample_name)
            GithubCommitStatusService.update(project_name, sample_name)   

        tmp_zip_file = GithubService.download_github_repository(access_token, full_name, branch)
        GithubService.extract_repository(tmp_zip_file)
        GithubWorkflowService.clone_github_repository(conll_files, project_name, username)
        if branch_syn == "arboratorgrew":
            if (branch != branch_syn and  branch_syn in GithubService.list_branches_repository(access_token, full_name)): 
                GithubService.delete_branch(access_token, full_name, branch_syn)    
            GithubService.create_new_branch_arborator(access_token, full_name, branch)

        
    @staticmethod 
    def clone_github_repository(files, project_name, username):
        for file in files:
            path_file = os.path.join(Config.UPLOAD_FOLDER, file)
            user_ids = GithubWorkflowService.preprocess_file(path_file, username)
            sample_name = file.split('.conllu')[0]
            GithubWorkflowService.create_sample(sample_name, path_file, project_name, user_ids)
            GithubCommitStatusService.create(project_name, sample_name)
            

    @staticmethod
    def preprocess_file(path_file, username):
        user_ids = {}
        user_ids["default"] = username
        file = SampleService.read_conll_from_disk(path_file)
        for line in file.rstrip().split("\n"):
            if "# user_id = " in line:
                user_id = line.split("# user_id = ")[-1]
                user_ids[user_id] = user_id
        return user_ids
        

    @staticmethod
    def create_sample(sample_name, path_file, project_name, users_ids):
        tokens_number = SampleService.convert_users_ids(path_file, users_ids)
        SampleService.add_or_keep_timestamps(path_file)
        SampleService.check_duplicated_sent_id(path_file)
        grew_samples = GrewService.get_samples(project_name)
        samples_names = [sa["name"] for sa in grew_samples]
        if sample_name not in samples_names:
            GrewService.create_sample(project_name, sample_name)
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
    
    
    @staticmethod
    def download_github_file_content(file_name, download_url):
        sample_name = file_name.split(".conllu")[0]
        raw_content = requests.get(download_url)
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        file = open(path_file, "w")
        file.write(raw_content.text)
        return sample_name, path_file


    @staticmethod
    def create_sample_from_github_file(file, download_url, username, project_name):
        sample_name, path_file =  GithubWorkflowService.download_github_file_content(file, download_url)
        user_ids = GithubWorkflowService.preprocess_file(path_file,username)
        GithubWorkflowService.create_sample(sample_name, path_file, project_name, user_ids)
        GithubCommitStatusService.create(project_name, sample_name)


    @staticmethod
    def commit_changes(access_token, full_name, updated_samples, project_name, username, message):
        
        project_id = ProjectService.get_by_name(project_name).id
        branch = GithubSynchronizationService.get_github_synchronized_repository(project_id).branch
        parent = GithubService.get_sha_base_tree(access_token, full_name, branch)
        tree = GithubService.create_tree(access_token,full_name, updated_samples, project_name, username, parent)
        sha = GithubService.create_commit(access_token, tree, parent, message, full_name)
        response =GithubService.update_sha(access_token, full_name, branch, sha)
        data = response.json()
        return data.get("object").get("sha")


    @staticmethod 
    def update_file_content(content, sha, message, url, access_token):
        headers = GithubService.base_header(access_token)
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {'sha': sha, 'message': message, 'content': encoded_content}
        response = requests.put(url, headers = headers, data = json.dumps(data))
        return response
    

    @staticmethod
    def check_pull(access_token, project_name):
        project = ProjectService.get_by_name(project_name)
        full_name = GithubSynchronizationService.get_github_synchronized_repository(project.id).repository_name
        branch = GithubSynchronizationService.get_github_synchronized_repository(project.id).branch
        sha = GithubSynchronizationService.get_github_synchronized_repository(project.id).base_sha
        base_tree = GithubService.get_sha_base_tree(access_token, full_name, branch)
        return sha != base_tree


    @staticmethod 
    def pull_changes(access_token, project_name, username, full_name, base_tree, modified_files):
        for file in modified_files:
            sample_name = file.get("filename").split(".conllu")[0]
            file_content= GithubService.get_file_content_by_commit_sha(access_token,full_name, file.get("filename"), base_tree)
            download_url = file_content.get("download_url")
            if file.get("status") == "added":
                GithubWorkflowService.create_sample_from_github_file(sample_name, download_url, username, project_name)
            if file.get("status") == "modified":
                GithubWorkflowService.pull_change_existing_sample(project_name, sample_name,username, download_url)
            if file.get("status") == "removed":
                GithubWorkflowService.delete_sample_from_project(project_name, sample_name)


    @staticmethod
    def pull_change_existing_sample(project_name, sample_name, username, download_url):
        
        content = requests.get(download_url).text 
        file_name = sample_name + "_modified.conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)

        with open(path_file, "w") as file:
            file.write(content)

        user_ids = GithubWorkflowService.preprocess_file(path_file, username)
        SampleService.convert_users_ids(path_file, user_ids)
        SampleService.add_or_keep_timestamps(path_file)
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
        
        conlls_strings = SampleService.split_conll_string_to_conlls_list(content)
        reply = grew_request("getConll", data={"project_id": project_name, "sample_id": sample_name},)
        sample_trees =SampleExportService.servSampleTrees(reply.get("data", {}))
        modified_sentences = []
        for conll in conlls_strings:
            for line in conll.rstrip().split("\n"):
                if "# sent_id = " in line:
                    sent_id = line.split("# sent_id = ")[-1] 
                    modified_sentences.append(sent_id)
        deleted_sentences = [sent_id for sent_id in sample_trees.keys() if not sent_id in modified_sentences]
        if deleted_sentences:
            data = {"project_id": project_name, "sample_id": sample_name, "sent_ids": json.dumps(deleted_sentences), "user_id": username}
            grew_request("eraseGraphs", data)
        
                
    @staticmethod
    def delete_file_from_github(access_token, project_name, full_name, sample_name):

        file_path = sample_name+".conllu"
        project_id = ProjectService.get_by_name(project_name).id
        branch = GithubSynchronizationService.get_github_synchronized_repository(project_id).branch
        GithubService.delete_file(access_token, full_name, file_path, branch)
        GithubCommitStatusService.delete(project_name, sample_name)
        new_base_tree_sha = GithubService.get_sha_base_tree(access_token, full_name, branch)
        GithubSynchronizationService.update_base_sha(project_id, full_name, new_base_tree_sha)


    @staticmethod
    def delete_sample_from_project(project_name, sample_name):
        project = ProjectService.get_by_name(project_name)
        GrewService.delete_sample(project_name, sample_name)
        SampleService.SampleBlindAnnotationLevelService.delete_by_sample_name(project.id, sample_name)


class GithubService: 
    @staticmethod    
    def base_header(access_token):
        return {"Authorization": "bearer " + access_token}
    

    @staticmethod
    def get_user_information(access_token):
        url = "https://api.github.com/user"
        headers =  GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        return data
    

    @staticmethod
    def get_user_email(access_token) -> str:
        url = "https://api.github.com/user/emails"
        headers =  GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        return data[0].get("email")
    
    
    @staticmethod    
    def get_repositories(access_token):
        repositories = []
        data = []
        url = "https://api.github.com/user/repos?per_page=100"
        headers = GithubService.base_header(access_token)
        first_page = requests.get(url, headers=headers)
        data = first_page.json()
        next_page = first_page
        while next_page.links.get('next', None) is not None:
            next_url = next_page.links['next']['url']
            next_page = requests.get(next_url, headers=headers)
            data.extend(next_page.json())
    
        for repo in data:
            repository = {}
            repository["name"] = repo.get("full_name")
            repository["owner_name"] = repo.get("owner").get("login")
            repository["owner_avatar"] = repo.get("owner").get("avatar_url")
            repositories.append(repository) 
        return repositories
      

    @staticmethod
    def list_branches_repository(access_token, full_name) -> List[str]:
        url = "https://api.github.com/repos/{}/branches".format(full_name)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers ) 
        data = response.json()
        return [branch.get("name") for branch in data if "dependabot" not in branch.get("name")]


    @staticmethod    
    def get_repository_files_from_specific_branch(access_token, full_name, branch):
        url = "https://api.github.com/repos/{}/contents/?ref={}".format(full_name, branch)
        headers = GithubService.base_header(access_token)
        response = requests.get(url , headers=headers)
        data = response.json()
        return data
    

    @staticmethod   
    def get_file_sha(access_token, full_name, file_path, branch):
        url = "https://api.github.com/repos/{}/contents/{}?ref={}".format(full_name, file_path, branch)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("sha")
    

    @staticmethod
    def get_default_branch(access_token, full_name):
        url = "https://api.github.com/repos/{}".format(full_name)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers )
        data = response.json()
        return data.get("default_branch")
    
    
    @staticmethod
    def get_sha_base_tree(access_token, full_name, branch):
        url = "https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch)
        headers =  GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        try:
            return data.get("object").get("sha")
        except:
            abort(400, "The Github repository doesn't exist anymore") 
           
        
    @staticmethod
    def create_blob_for_updated_file(access_token, full_name, content):
        data = {"content": content, "encoding": "utf-8"}
        url = "https://api.github.com/repos/{}/git/blobs".format(full_name)
        headers = GithubService.base_header(access_token)
        response = requests.post(url, headers=headers , data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
    

    @staticmethod 
    def create_tree(access_token, full_name, updated_samples, project_name, username, base_tree):
        tree = []
        sample_names, sample_content_files = GrewService.get_samples_with_string_contents(project_name, updated_samples)
        for sample_name, sample in zip(sample_names,sample_content_files):
            if (username == 'Validated'):
                owner_username = UserService.get_by_id(current_user.id).username
                content = GrewService.get_validated_trees_filled_up_with_owner_trees(project_name, sample_name, owner_username)
            else:
                content = sample.get(username)
            sha = GithubService.create_blob_for_updated_file(access_token, full_name, content)
            blob = {"path": sample_name+".conllu", "mode":"100644", "type":"blob", "sha": sha}
            tree.append(blob)

        url = "https://api.github.com/repos/{}/git/trees".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {"tree": tree, "base_tree": base_tree}

        response = requests.post(url, headers=headers, data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
        
    
    @staticmethod
    def create_commit(access_token, tree, parent, message, full_name):
        url = "https://api.github.com/repos/{}/git/commits".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {"tree": tree, "parents": [parent], "message": message}

        response = requests.post(url, headers=headers, data = json.dumps(data) )
        data = response.json()
        return data.get("sha")


    @staticmethod
    def update_sha(access_token, full_name, branch, sha):
        url = "https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch)
        headers = GithubService.base_header(access_token)
        data = {"sha": sha}

        response = requests.patch(url, headers=headers,  data= json.dumps(data))
        return response
    

    @staticmethod
    def create_github_repository(access_token, data):
        url = "https://api.github.com/user/repos"
        headers = GithubService.base_header(access_token)

        response = requests.post(url, headers=headers, data = json.dumps(data) )
        return response
    

    @staticmethod
    def create_new_branch_arborator(access_token, full_name, default_branch):
        url = "https://api.github.com/repos/{}/git/refs".format(full_name)
        headers =  GithubService.base_header(access_token)
        sha = GithubService.get_sha_base_tree(access_token, full_name, default_branch)
        data = {
            "ref": "refs/heads/arboratorgrew",
            "sha": sha
        }
        response = requests.post(url, headers=headers, data = json.dumps(data))
        return response.json()
    

    @staticmethod
    def get_tree(access_token, full_name, base_tree):
        url = "https://api.github.com/repos/{}/git/trees/{}".format(full_name, base_tree)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        try: 
            data = response.json()
            return data.get("tree")
        except:
            return []
    

    @staticmethod
    def get_file_content_by_commit_sha(access_token, full_name, file_path, sha):
        url = "https://api.github.com/repos/{}/contents/{}?ref={}".format(full_name, file_path, sha)
        headers = GithubService.base_header(access_token)

        response = requests.get(url, headers=headers)
        data = response.json()
        return data
    

    @staticmethod
    def delete_file(access_token, full_name, file_path, branch):
        url = "https://api.github.com/repos/{}/contents/{}".format(full_name, file_path)
        headers = GithubService.base_header(access_token)
        sha = GithubService.get_file_sha(access_token, full_name, file_path, branch)
        data = {"sha": sha, "message": "file deleted from github", "branch": branch}

        response = requests.delete(url, headers=headers , data=json.dumps(data))
        return response


    @staticmethod
    def create_pull_request(access_token, full_name, username, arborator_branch, branch, title):
        url = "https://api.github.com/repos/{}/pulls".format(full_name)
        headers = GithubService.base_header(access_token)
        head = username + ":" + arborator_branch
        data = {"title": title, "head": head, "base": branch}
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if not response:
            error = response.json()['errors'][0].get("message") 
            abort(422, error)

    
    @staticmethod 
    def merge_branch(access_token, full_name, base, head):
        url = "https://api.github.com/repos/{}/merges".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {"base": base, "head": head}
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response


    @staticmethod
    def delete_branch(access_token, full_name, base):
        url = "https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, base)
        headers = GithubService.base_header(access_token)
        response = requests.delete(url, headers=headers)
        return response
    

    @staticmethod
    def compare_two_commits(access_token, full_name, previous_commit, new_commit):
        url = 'https://api.github.com/repos/{}/compare/{}...{}'.format(full_name, previous_commit, new_commit)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        modified_files = [{"filename": file.get("filename"), "status": file.get("status")} for file in data.get('files')]
        return modified_files
    
    
    @staticmethod
    def download_github_repository(access_token, full_name, branch):
        url = 'https://api.github.com/repos/{}/zipball/{}'.format(full_name, branch)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers, stream=True)
        file_name = 'tmp.zip'
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        if response.status_code == 200:
            with open(path_file, "wb") as file:
                 file.write(response.content)
        return path_file
        

    @staticmethod
    def extract_repository(file_path):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for file in zip_file.namelist():
                filename = os.path.basename(file)
                if not filename:
                    continue
                if extension.search(filename):
                    source = zip_file.open(file)
                    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    destination = open(file_path, "wb")
                    with source, destination:
                        shutil.copyfileobj(source, destination)
                        GithubService.check_large_file(file_path)


    @staticmethod
    def check_large_file(file_path):
        file_size = (os.stat(file_path).st_size)/(1024*1024)
        if file_size > 13:
            abort(413, "it contains a large file")

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
    

    @staticmethod
    def delete(project_name, sample_name):
        project = ProjectService.get_by_name(project_name)
        github_commit_status: GithubCommitStatus = GithubCommitStatus.query.filter(GithubCommitStatus.project_id == project.id).filter(GithubCommitStatus.sample_name == sample_name).first()
        if github_commit_status:
            db.session.delete(github_commit_status)
            db.session.commit()

