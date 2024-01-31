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

    @responds(schema=GithubRepositorySchema, api=api)
    def get(self, project_name):
        project = ProjectService.get_by_name(project_name)
        return GithubRepositoryService.get_by_project_id(project.id)
    
    def post(self, project_name):
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
        project = ProjectService.get_by_name(project_name)
        GithubRepositoryService.delete_by_project_id(project.id)
        return { "status": "ok" }
    
@api.route("/github")
class UserGithubRepositories(Resource):

    def get(self):
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubService.get_repositories(github_access_token)
    
@api.route("/github/branch")
class GithubRepositoryBranch(Resource):

    def get(self):
        data = request.args
        full_name = data.get("full_name")
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubService.list_repository_branches(github_access_token, full_name)
    
@api.route("/<string:project_name>/synchronize/commit")
class GithubCommitResource(Resource):

    def get(self, project_name):
        project = ProjectService.get_by_name(project_name)
        return GithubCommitStatusService.get_changes_number(project.id)
    
    def post(self, project_name):
        data = request.get_json()
        commit_message = data.get("commitMessage")
        project = ProjectService.get_by_name(project_name)
        modified_samples = GithubCommitStatusService.get_modified_samples(project.id)
        sha = GithubWorkflowService.commit_changes(modified_samples, project_name, commit_message)

        GithubRepositoryService.update_sha(project.id, sha)
        GithubCommitStatusService.reset_samples(project.id, modified_samples)
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/pull")
class GithubPullResource(Resource):

    def get(self, project_name):
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubWorkflowService.check_pull(github_access_token, project_name)
    
    def post(self, project_name):
        GithubWorkflowService.pull_changes(project_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/pull-request")
class GithubPullRequestResource(Resource):

    def post(self,project_name):
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
    
@api.route("/<string:project_name>/synchronize/<string:file_name>")
class GithubFileResource(Resource):

    def delete(self, project_name, file_name):
        access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubWorkflowService.delete_file_from_github(access_token, project_name, file_name )
