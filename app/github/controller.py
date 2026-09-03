from flask_restx import Namespace, Resource
from flask import abort, request
from flask_login import current_user
from flask_accepts.decorators.decorators import responds

from app.projects.service import ProjectService
from app.user.service import UserService
from app.projects.service import LastAccessService, ProjectAccessService
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
        ProjectAccessService.check_admin_access(project.id)
        
        sync_repo = GithubRepositoryService.get_by_project_id(project.id)
        if sync_repo:
            # Check if current user has access to the GitHub repository
            user = UserService.get_by_id(current_user.id)
            has_github_access = GithubService.check_user_has_github_access(
                user.github_access_token,
                sync_repo.repository_name
            )
            result = {
                'id': sync_repo.id,
                'project_id': sync_repo.project_id,
                'user_id': sync_repo.user_id,
                'repository_name': sync_repo.repository_name,
                'branch': sync_repo.branch,
                'base_sha': sync_repo.base_sha,
                'has_github_access': has_github_access
            }
            return result
        return sync_repo
    
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
        ProjectAccessService.check_admin_access(project.id)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token

        # Check if repository branch is empty and create an initial commit if it is
        if GithubService.is_repository_branch_empty(github_access_token, full_name):
            GithubService.create_initial_empty_commit(github_access_token, full_name, "main")
            branch_import = "main"
            branch_sync = "main"

        GithubWorkflowService.import_files_from_github(full_name, project_name, branch_import, branch_sync)
        sha = GithubService.get_sha_base_tree(github_access_token, full_name, branch_sync)
        data = { "project_id": project.id, "user_id": current_user.id, "repository_name": full_name, "branch": branch_sync, "base_sha": sha }
        GithubRepositoryService.create(data)

    def delete(self, project_name):
        """Delete synchronization"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
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
        """Get the git-like status of synchronized samples"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        return GithubCommitStatusService.get_modified_samples(project_name)
    
    def post(self, project_name):
        """Create and push a commit for the selected samples"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        commit_message = data.get("commitMessage")
        modified_samples_names = data.get("sampleNames", [])
        if not modified_samples_names:
            abort(400, "No samples selected for commit")
        sha = GithubWorkflowService.commit_changes(modified_samples_names, project_name, commit_message)

        from app.trees.staging_service import StagingService
        for sample_name in modified_samples_names:
            StagingService.mark_as_pushed(project.id, sample_name, current_user.username)
        
        GithubRepositoryService.update_sha(project.id, sha)
        return { "status": "ok" }

    def patch(self, project_name):
        """Reset selected samples to the synchronized GitHub base state"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        sample_names = data.get("sampleNames", [])
        if not sample_names:
            abort(400, "No samples selected for reset")
        GithubCommitStatusService.reset_samples(project_name, sample_names)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/rename")
class GithubRenameSample(Resource):
    def post(self, project_name):
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        old_sample_name = data.get("oldName")
        old_file_name = old_sample_name+".conllu"
        new_sample_name = data.get("newName")
        new_file_name = new_sample_name+".conllu"
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        repo = GithubRepositoryService.get_by_project_id(project.id)

        new_sha = GithubService.rename_file_in_github_repo(
            github_access_token,
            repo.repository_name,
            old_file_name,
            new_file_name,
            repo.branch,
        ) or GithubService.get_sha_base_tree(github_access_token, repo.repository_name, repo.branch)
        GithubRepositoryService.update_sha(project.id, new_sha)
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/stage")
class GithubStageResource(Resource):
    def post(self, project_name):
        """Stage all trees of one user for a sample."""
        data = request.get_json() or {}
        sample_name = data.get("sample_name")
        tree_user_id = data.get("tree_user_id")

        if not all([sample_name, tree_user_id]):
            abort(400, "sample_name and tree_user_id are required")

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        ProjectAccessService.check_admin_access(project.id)

        from app.trees.staging_service import StagingService
        staged_count = StagingService.stage_sample(
            project_name,
            project.id,
            sample_name,
            tree_user_id,
            current_user.username,
        )

        return {"status": "ok", "staged_count": staged_count}

    def delete(self, project_name):
        """Unstage a tree for GitHub push"""
        data = request.get_json()
        sample_name = data.get("sample_name")
        sent_id = data.get("sent_id")
        tree_user_id = data.get("tree_user_id")
        
        if not all([sample_name, sent_id, tree_user_id]):
            abort(400, "sample_name, sent_id, and tree_user_id are required")
        
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        
        # Check if user is admin
        ProjectAccessService.check_admin_access(project.id)
        
        # Unstage the tree
        from app.trees.staging_service import StagingService
        StagingService.unstage(project.id, sample_name, sent_id, tree_user_id)
        
        return { "status": "ok" }

# route for pushing new samples immediatly (independently from other pending changes)
@api.route("/<string:project_name>/synchronize/commit_samples")
class GithubCommitSamples(Resource):
    def post(self, project_name):
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        sha = GithubWorkflowService.commit_changes(data['new_samples'], project_name, "new samples added in ArboratorGrew")
        GithubRepositoryService.update_sha(project.id, sha)

@api.route("/<string:project_name>/synchronize/pull")
class GithubPullResource(Resource):
    """Class contains methods deals with the pulls"""
    def get(self, project_name):
        """Check if there is changes to pull"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return GithubWorkflowService.check_pull(github_access_token, project_name)
    
    def post(self, project_name):
        """Pull changes"""
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        GithubWorkflowService.pull_changes(project_name)
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")
        return { "status": "ok" }

@api.route("/<string:project_name>/synchronize/pull-preview")
class GithubPullPreviewResource(Resource):
    """preview which files would be affected by a pull"""
    def get(self, project_name):
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        return GithubWorkflowService.preview_pull_changes(project_name)

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
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        branch = data.get("branch")
        title = data.get("title")

        user = UserService.get_by_id(current_user.id)
        access_token = user.github_access_token

        repo = GithubRepositoryService.get_by_project_id(project.id)

        GithubService.create_pull_request(access_token, repo.repository_name, user.username, repo.branch, branch, title)
        return { "status": "ok" }
    
@api.route("/<string:project_name>/synchronize/files")
class GithubFileResource(Resource):

    def patch(self, project_name):
        project = ProjectService.get_by_name(project_name)
        ProjectAccessService.check_admin_access(project.id)
        data = request.get_json()
        sample_names = data.get("sampleNames")
        access_token = UserService.get_by_id(current_user.id).github_access_token
        GithubWorkflowService.delete_files_from_github(access_token, project_name, sample_names)
