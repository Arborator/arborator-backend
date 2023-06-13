from flask_restx import Namespace, Resource, reqparse
from flask import abort
from flask_login import current_user

from ..projects.service import ProjectService, LastAccessService
from ..user.service import UserService
from .service import GithubSynchronizationService, GithubService, GithubWorkflowService, GithubCommitStatusService


api = Namespace("Github", description="Endpoints for dealing with github repositories") 


@api.route("/<string:project_name>/<string:username>/synchronize-github")
class GithubSynchronizationResource(Resource):

    def get(self, project_name: str, username: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        try:
            repository = GithubSynchronizationService.get_github_synchronized_repository(project.id).repository_name
            return repository
        except: 
            return ''
    
    
    def post(self, project_name: str, username:str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        parser.add_argument(name="branchImport")
        parser.add_argument(name="branchSyn")
        args = parser.parse_args()

        repository_name = args.get("repositoryName")
        branch_import = args.get("branchImport")
        branch_syn = args.get("branchSyn")

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
    
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubWorkflowService.import_files_from_github(github_access_token, repository_name, project_name, username, branch_import, branch_syn)
        sha = GithubService.get_sha_base_tree(github_access_token, repository_name, branch_syn)
        GithubSynchronizationService.synchronize_github_repository(current_user.id, project.id, repository_name, branch_syn, sha)
        
        return {"status": "success"}
    

    def delete(self, project_name: str, username: str):

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        GithubSynchronizationService.delete_synchronization(current_user.id, project.id)
        
        return {"status": "success"}

    
@api.route("/<string:project_name>/<string:username>/github")
class GithubRepositoryResource(Resource):

    def get(self, project_name: str, username: str):
        github_access_token = UserService.get_by_username(username).github_access_token
        return GithubService.get_repositories(github_access_token)
    
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
        modified_samples = GithubCommitStatusService.get_modified_samples(project.id)
        sha = GithubWorkflowService.commit_changes(github_access_token, repository_name, modified_samples, project_name, user_type, github_message)
        
        GithubSynchronizationService.update_base_sha(project.id, repository_name, sha)
        GithubCommitStatusService.reset_samples(project.id, modified_samples)
    

@api.route("/<string:project_name>/<string:username>/synchronize-github/pull")
class GithubPullResource(Resource):

    def get(self, project_name: str, username: str):
        github_access_token = UserService.get_by_username(username).github_access_token
        return GithubWorkflowService.check_pull(github_access_token, project_name)
    
    def post(self, project_name: str, username: str):

        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        args = parser.parse_args()
        full_name = args.get("repositoryName")

        project_id = ProjectService.get_by_name(project_name).id
        access_token = UserService.get_by_username(username).github_access_token
        branch = GithubSynchronizationService.get_github_synchronized_repository(project_id).branch
        sha = GithubSynchronizationService.get_github_synchronized_repository(project_id).base_sha
        base_tree = GithubService.get_sha_base_tree(access_token, full_name, branch)

        if GithubWorkflowService.check_pull(access_token, project_name):
            modified_files = GithubService.compare_two_commits(access_token, full_name, sha, base_tree)
            GithubWorkflowService.pull_changes(access_token, project_name, username, full_name, base_tree, modified_files)
            GithubSynchronizationService.update_base_sha(project_id, full_name, base_tree)
            LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/<string:username>/synchronize-github/pull-request")
class GithubPullRequestResource(Resource):

    def post(self, project_name: str, username: str):

        parser =   parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        parser.add_argument(name="branch")
        parser.add_argument(name="title")
        args = parser.parse_args()

        full_name = args.get("repositoryName")
        branch = args.get("branch")
        title = args.get("title")

        project_id = ProjectService.get_by_name(project_name).id
        access_token = UserService.get_by_username(username).github_access_token
        branch_base = GithubSynchronizationService.get_github_synchronized_repository(project_id).branch
       
        if branch == branch_base:
            abort(422, "No pulls between {} and {}. You’ll need to use two different branches".format(branch, branch_base))
        else:
            GithubService.create_pull_request(access_token, full_name, username, branch_base , branch, title)


@api.route("/<string:project_name>/<string:username>/synchronize-github/<string:file_name>")
class GithubRepositoryFileResource(Resource):

    def delete(self, project_name: str, username: str, file_name):
        access_token = UserService.get_by_username(username).github_access_token
        project_id = ProjectService.get_by_name(project_name).id
        full_name = GithubSynchronizationService.get_github_synchronized_repository(project_id).repository_name
        GithubWorkflowService.delete_file_from_github(access_token, project_name, full_name,file_name )

