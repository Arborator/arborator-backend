from flask_restx import Namespace, Resource, reqparse
from ..projects.service import ProjectService
from ..user.service import UserService
from .service import GithubRepositoryService, GithubService
from flask_login import current_user

api = Namespace("Github", description="Endpoints for dealing with github repositories") 


@api.route("/<string:project_name>/<string:username>/github-repository")
class SynchronizedGithubRepositoryController(Resource):
    def get(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        repository = GithubRepositoryService.get_github_repository_per_user(user_id, project.id)
        return repository
    
    def post(self, project_name: str, username:str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        args = parser.parse_args()
        repository_name = args.get("repositoryName")

        user_ids = {}
        user_ids["default"] = username
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubRepositoryService.synchronize_github_repository(user_id, project.id, repository_name)
        GithubService.import_files_from_github(github_access_token, repository_name, project_name,user_ids)

        return {"status": "success"}
    
    def delete(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        GithubRepositoryService.delete_synchronization(user_id, project.id)
        
        return {"status": "success"}

    
@api.route("/<string:project_name>/me/github")
class GithubRepository(Resource):
    def get(self, project_name):
        return GithubService.get_repositories(UserService.get_by_id(current_user.id).github_access_token)
    
    def post(self, project_name):

        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        parser.add_argument(name="description")
        parser.add_argument(name="visibility")
        args = parser.parse_args()

        name = args.get("repositoryName")
        description = args.get("description")
        visibility = args.get("visibility")
        private = True if visibility == "private" else False
        data = {
            "name" : name,
            "description": description,
            "private": private
        }
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubService.create_github_repository(github_access_token, data)
        

@api.route("/<string:project_name>/<string:username>/commit")
class GithubCommit(Resource):
    def post(self, project_name:str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="message")
        parser.add_argument(name="repositoryName")
        args = parser.parse_args()
        github_message = args.get("message")
        repository_name = args.get("repositoryName")
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubService.commit_changes_repository(github_access_token, repository_name, project_name, github_message)
