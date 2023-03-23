import os
import requests
import base64
import json
from flask import abort
from app import db
from app.config import MAX_TOKENS, Config
from .model import GithubRepository
from app.samples.service import convert_users_ids, add_or_keep_timestamps
from app.utils.grew_utils import GrewService



class GithubRepositoryService:

    @staticmethod
    def get_github_repository_per_user(user_id, project_id):
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


class GithubService:

    @staticmethod
    def import_files_from_github(acess_token, full_name, project_name, user_ids):
        repository_files = GithubService.get_repository_files(acess_token, full_name)
        for file in repository_files:
            sample_name, path_file = GithubService.create_file_from_sample_content(file.get('name'), file.get('download_url'))
            GithubService.create_sample_github_file(sample_name, path_file, project_name, user_ids)

    
    @staticmethod 
    def create_file_from_sample_content(file_name, download_url):
        sample_name = file_name.split(".")[0]
        raw_content = requests.get(download_url)
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        file = open(path_file, "w")
        file.write(raw_content.text)

        return sample_name, path_file
    

    @staticmethod
    def create_sample_github_file(sample_name, path_file, project_name, users_ids):
        tokens_number = convert_users_ids(path_file, users_ids )
        add_or_keep_timestamps(path_file)
        if tokens_number > MAX_TOKENS:
            abort(406, "Too big: Sample files on ArboratorGrew should have less than {max} tokens.".format(max=MAX_TOKENS))
        GrewService.create_sample(project_name, sample_name)
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)

    
    @staticmethod
    def commit_changes_repository(access_token, full_name, project_name, message):
        files = GithubService.get_repository_files(access_token, full_name)
        for file in files:
            file_name =file.get('name')
            sha = GithubService.get_file_sha(access_token, full_name, file_name)
            file = [ file_name.split(".")[0]]
            sample_name, sample_with_string_content = GrewService.get_samples_with_string_contents(project_name,file)
            for sample in sample_with_string_content:
                for  user in sample:
                    if user != "last":
                        content= sample[user]
            url = "https://api.github.com/repos/{}/contents/{}".format(full_name, file_name)
            GithubService.update_file_content(content, sha, message, url, access_token)



    @staticmethod 
    def update_file_content(content, sha, message, url, access_token):
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {'sha': sha, 'message': message, 'content': encoded_content}
        response = requests.put(url, headers = GithubService.base_header(access_token), data = json.dumps(data))
        return response


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
    def get_list_organizations(access_token):
        response = requests.get("https://api.github.com/user/memberships/orgs", headers = GithubService.base_header(access_token))
        data = response.json()
        return [ [membership.get("organization").get("login"), membership.get("organization").get("avatar_url")] for membership in data]
    

    @staticmethod
    def create_github_repository(access_token, data):
        response = requests.post("https://api.github.com/user/repos", headers = GithubService.base_header(access_token), data = json.dumps(data) )
        return response




    
   



