import requests
from typing import List
from app import db
from .model import GithubRepository
from ..projects.model import Project
from ..user.model import User



class GithubRepositoryService:

    @staticmethod
    def get_github_repository_per_user(user_id, project_id):
        github_repository: GithubRepository = GithubRepository.query.filter(GithubRepository.user_id == user_id).filter(GithubRepository.project_id == project_id).first()
        return github_repository.repository_name
    

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
    
    


    
   



