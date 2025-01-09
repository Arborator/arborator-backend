from flask_restx import Namespace, Resource
from flask import request
from flask_login import current_user
from flask_accepts.decorators.decorators import responds

from app.projects.service import ProjectService
from app.user.service import UserService
from app.projects.service import LastAccessService
from .service import GithubRepositoryService, GithubService, GithubWorkflowService, GithubCommitStatusService
from .schema import GithubRepositorySchema

api = Namespace("Github", description="Endpoints for dealing with github repositories")

@api.route("/<string:project_name>/synchronize")
class GithubSynchronizationResource(Resource):
    """Class contains endpoints that deals with the synchronization"""
    @responds(schema=GithubRepositorySchema, api=api)
    def get(self, project_name):
        """Get the synchronized repository"""
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return GithubRepositoryService.get_by_project_id(project.id)
    
    def post(self, project_name):
        """Create synchronization

        Args:
            project_name (str)
            full_name(str): the name of the repository to be synchronized
            branch_import(str): branch used for the import
            branch_sync(str): branch to be used for the synchronization
        """
        data = request.get_json()
        full_name = data.get("fullName")
        branch_import = data.get("branchImport")
        branch_sync = data.get("branchSync")

        project = ProjectService.get_by_name(project_name)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token

        GithubWorkflowService.import_files_from_github(full_name, project_name, branch_import, branch_sync)
        sha = GithubService.get_sha_base_tree(github_access_token, full_name, branch_sync)
        data = { "project_id": project.id, "user_id": current_user.id, "repository_name": full_name, "branch": branch_sync, "base_sha": sha }
        GithubRepositoryService.create(data)

    def delete(self, project_name):
        """Delete synchronization"""
        project = ProjectService.get_by_name(project_name)
        GithubRepositoryService.delete_by_project_id(project.id)
        return { "status": "ok" }
    
@api.route("/github")
class UserGithubRepositories(Resource):
    """Class contains the endpoint to get user repositories"""
    def get(self):
        """List user github repos"""
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubService.get_repositories(github_access_token)
    
@api.route("/github/branch")
class GithubRepositoryBranch(Resource):
    """class contains the endpoint to get the branch of specific repo"""
    def get(self):
        data = request.args
        full_name = data.get("full_name")
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubService.list_repository_branches(github_access_token, full_name)
    
@api.route("/<string:project_name>/synchronize/commit")
class GithubCommitResource(Resource):
    """Class contains endpoints related to commit"""
    def get(self, project_name):
        """Get the number of changes to be committed"""
        project = ProjectService.get_by_name(project_name)
        modified_samples = GithubCommitStatusService.get_modified_samples(project.id)
        for sample in modified_samples:
            diff_string = GithubCommitStatusService.compare_changes_sample(project_name, sample["sample_name"])
            sample["diff"] = diff_string
        return modified_samples
    
    def post(self, project_name):
        """Create and push a commit"""
        data = request.get_json()
        commit_message = data.get("commitMessage")
        project = ProjectService.get_by_name(project_name)
        modified_samples = GithubCommitStatusService.get_modified_samples(project.id)
        modified_samples_names = [sample["sample_name"] for sample in modified_samples]
        sha = GithubWorkflowService.commit_changes(modified_samples_names, project_name, commit_message)
        
        GithubRepositoryService.update_sha(project.id, sha)
        GithubCommitStatusService.reset_samples(project.id, modified_samples_names)
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/pull")
class GithubPullResource(Resource):
    """Class contains methods deals with the pulls"""
    def get(self, project_name):
        """Check if there is changes to pull"""
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubWorkflowService.check_pull(github_access_token, project_name)
    
    def post(self, project_name):
        """Pull changes"""
        GithubWorkflowService.pull_changes(project_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/pull-request")
class GithubPullRequestResource(Resource):
    """Class deals with pull requests"""
    def post(self,project_name):
        """_summary_

        Args:
            project_name (str)
            branch (str) 
            title (str)
        """
        data = request.get_json()
        branch = data.get("branch")
        title = data.get("title")
        user = UserService.get_by_id(current_user.id)

        project_id = ProjectService.get_by_name(project_name).id
        access_token = user.github_access_token
        branch_base = GithubRepositoryService.get_by_project_id(project_id).branch
        full_name = GithubRepositoryService.get_by_project_id(project_id).repository_name

        GithubService.create_pull_request(access_token, full_name, user.username, branch_base , branch, title)
        return { "status": "ok" }
    
@api.route("/<string:project_name>/synchronize/files")
class GithubFileResource(Resource):

    def patch(self, project_name):
        data = request.get_json()
        sample_names = data.get("sampleNames")
        access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubWorkflowService.delete_files_from_github(access_token, project_name, sample_names)
