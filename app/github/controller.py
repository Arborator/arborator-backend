from flask_restx import Namespace, Resource, reqparse
from flask import request
from ..projects.service import ProjectService, LastAccessService
from ..user.service import UserService
from .service import GithubSynchronizationService, GithubService, GithubWorkflowService, GithubCommitStatusService
from flask_login import current_user

api = Namespace("Github", description="Endpoints for dealing with github repositories") 


@api.route("/<string:project_name>/<string:username>/synchronize-github")
class GithubSynchronizationResource(Resource):

    def get(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        repository, sha = GithubSynchronizationService.get_github_synchronized_repository(project.id)
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
        GithubWorkflowService.import_files_from_github(github_access_token, repository_name, project_name, username, branch)
        sha = GithubService.get_sha_base_tree(github_access_token, repository_name, "arboratorgrew" )
        GithubSynchronizationService.synchronize_github_repository(user_id, project.id, repository_name, sha)
        
        return {"status": "success"}
    

    def delete(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        user_id = UserService.get_by_username(username).id
        GithubSynchronizationService.delete_synchronization(user_id, project.id)
        
        return {"status": "success"}

    
@api.route("/<string:project_name>/<string:username>/github")
class GithubRepositoryResource(Resource):
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
class GithubRepositoryBranchResource(Resource):
    def get(self, project_name: str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="full_name")
        args = parser.parse_args()
        full_name = args.get("full_name")

        github_access_token = UserService.get_by_username(username).github_access_token
        return GithubService.list_branches_repository(github_access_token, full_name)

        
@api.route("/<string:project_name>/<string:username>/synchronize-github/commit")
class GithubCommitResource(Resource):
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
        project = ProjectService.get_by_name(project_name)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        modified_samples = GithubCommitStatusService.get_modified_samples(ProjectService.get_by_name(project_name).id)
        sha = GithubWorkflowService.commit_changes(github_access_token, repository_name, modified_samples,project_name, user_type, github_message)
        GithubSynchronizationService.update_base_sha(project.id, repository_name, sha)
        GithubCommitStatusService.reset_samples(ProjectService.get_by_name(project_name).id, modified_samples)
    

@api.route("/<string:project_name>/<string:username>/synchronize-github/pull")
class GithubPullResource(Resource):

    def get(self, project_name: str, username: str):
        user = UserService.get_by_username(username)
        return GithubWorkflowService.check_pull(user.github_access_token, project_name)
    
    def post(self, project_name: str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        args = parser.parse_args()
        full_name = args.get("repositoryName")
        project = ProjectService.get_by_name(project_name)
        
        user = UserService.get_by_username(username)
        if GithubWorkflowService.check_pull(user.github_access_token, project_name):
            base_tree = GithubService.get_sha_base_tree(user.github_access_token, full_name, "arboratorgrew")
            GithubWorkflowService.pull_changes(user.github_access_token,project_name,username, full_name,base_tree)
            GithubSynchronizationService.update_base_sha(project.id, full_name, base_tree)
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/<string:username>/synchronize-github/<string:file_name>")
class GithubRepositoryFileResource(Resource):

    def delete(self, project_name: str, username: str, file_name):
        user = UserService.get_by_username(username)
        project = ProjectService.get_by_name(project_name)
        full_name = GithubSynchronizationService.get_github_synchronized_repository(project.id)[0]
        GithubWorkflowService.delete_file_from_github(user.github_access_token, project_name, full_name,file_name )

