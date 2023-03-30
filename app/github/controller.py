from flask_restx import Namespace, Resource, reqparse
from flask import request
from ..projects.service import ProjectService
from ..user.service import UserService
from .service import GithubSynchronizationService, GithubService, GithubWorkflowService, GithubCommitStatusService
from flask_login import current_user

api = Namespace("Github", description="Endpoints for dealing with github repositories") 


@api.route("/<string:project_name>/<string:username>/synchronize-github")
class GithubSynchronization(Resource):

    def get(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        repository = GithubSynchronizationService.get_github_synchronized_repository(user_id, project.id)
        return repository
    
    
    def post(self, project_name: str, username:str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        parser.add_argument(name="branch")
        args = parser.parse_args()

        repository_name = args.get("repositoryName")
        branch = args.get("branch")
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubSynchronizationService.synchronize_github_repository(user_id, project.id, repository_name)
        GithubWorkflowService.import_files_from_github(github_access_token, repository_name, project_name, username, branch)

        return {"status": "success"}
    

    def delete(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        GithubSynchronizationService.delete_synchronization(user_id, project.id)
        
        return {"status": "success"}

    
@api.route("/<string:project_name>/<string:username>/github")
class GithubRepository(Resource):
    def get(self, project_name: str, username: str):
        return GithubService.get_repositories(UserService.get_by_username(username).github_access_token)
    
    def post(self, project_name: str, username: str):

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
        github_access_token = UserService.get_by_username(username).github_access_token
        GithubService.create_github_repository(github_access_token, data)


@api.route("/<string:project_name>/<string:username>/github/branch")
class GithubRepositoryBranch(Resource):
    def get(self, project_name: str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="full_name")
        args = parser.parse_args()
        full_name = args.get("full_name")

        github_access_token = UserService.get_by_username(username).github_access_token
        return GithubService.list_branches_repository(github_access_token, full_name)

        

@api.route("/<string:project_name>/<string:username>/synchronize-github/commit")
class GithubCommit(Resource):
    def get(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        return GithubCommitStatusService.get_changes_number(project.id)

    def post(self, project_name:str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="message")
        parser.add_argument(name="repositoryName")
        parser.add_argument(name="userType")
        args = parser.parse_args()
        github_message = args.get("message")
        repository_name = args.get("repositoryName")
        user_type = args.get("userType")
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        modified_samples = GithubCommitStatusService.get_modified_samples(ProjectService.get_by_name(project_name).id)
        GithubWorkflowService.commit_changes(github_access_token, repository_name, modified_samples,project_name, user_type, github_message)
        GithubCommitStatusService.reset_samples(ProjectService.get_by_name(project_name).id, modified_samples)