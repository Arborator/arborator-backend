import os
import requests
import base64
import json
import re 
import shutil
import zipfile
from difflib import unified_diff
from typing import List

from flask import abort
from flask_login import current_user

from app import db
from app.config import Config
from app.projects.service import ProjectService
from app.utils.grew_utils import GrewService, grew_request , SampleExportService
from app.user.service import UserService
from app.trees.staging_service import StagingService
import app.samples.service as SampleService

from .model import GithubRepository


extension = re.compile("^.*\.(conllu)$")

USERNAME = 'validated'
CONLL = '.conllu'
class GithubRepositoryService:
    """Class contains the methods that deal with GithubRepository entity """
    @staticmethod
    def get_by_project_id(project_id):
        """Get GithubRepository entity by project_id

        Args:
            project_id (int)

        Returns:
           GithubRepository
        """
        return GithubRepository.query.filter(GithubRepository.project_id == project_id).first()
    
    @staticmethod
    def create(new_attrs):
        """Create new GithubRepository entity"""
        github_repository = GithubRepository(**new_attrs)
        db.session.add(github_repository)
        db.session.commit()
    
    @staticmethod
    def update_sha(project_id, sha):
        """
            Every commit or pull the value of sha (last commit hash) is changed 
            and for that we need to update the sha of the synchronized repo
        Args:
            - project_id(int)
            - sha(str)
        """
        github_repository = GithubRepository.query.filter_by(project_id=project_id).first()
        if github_repository:
            github_repository.base_sha = sha
            db.session.commit()
        
    @staticmethod
    def delete_by_project_id(project_id):
        """Delete synchronized github repository by the project id

        Args:
            project_id (int)
        """
        github_repository = GithubRepository.query.filter_by(project_id=project_id).first()
        db.session.delete(github_repository)
        db.session.commit()

class GithubCommitStatusService:
    """Build git-like status information from AG content and the synchronized GitHub base commit."""

    @staticmethod
    def _get_sync_context(project_name):
        project = ProjectService.get_by_name(project_name)
        sync_repository = GithubRepositoryService.get_by_project_id(project.id)
        if not sync_repository:
            abort(404)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        return project, sync_repository, github_access_token

    @staticmethod
    def _list_base_samples(access_token, repository_name, ref):
        repository_files = GithubService.get_repository_files_of_branch(access_token, repository_name, ref)
        return {
            file.get("name").split(CONLL)[0]
            for file in repository_files
            if file.get("name") and extension.search(file.get("name"))
        }

    @staticmethod
    def _get_base_sample_content(access_token, repository_name, base_sha, sample_name):
        file_metadata = GithubService.get_file_content_by_commit_sha(access_token, repository_name, sample_name + CONLL, base_sha)
        download_url = file_metadata.get("download_url")
        if not download_url:
            return ""
        return requests.get(download_url).text

    @staticmethod
    def _build_diff(base_content, current_content, sample_name):
        diff = unified_diff(
            base_content.splitlines(),
            current_content.splitlines(),
            fromfile=sample_name + CONLL,
            tofile=sample_name + CONLL,
            lineterm=''
        )
        return '\n'.join(list(diff))

    @staticmethod
    def _count_changed_lines(diff_string):
        changes = 0
        added_lines = 0
        deleted_lines = 0

        def count_block():
            nonlocal changes, added_lines, deleted_lines
            if added_lines or deleted_lines:
                changes += max(added_lines, deleted_lines)
                added_lines = 0
                deleted_lines = 0

        for line in diff_string.splitlines():
            if not line or line.startswith('+++') or line.startswith('---'):
                continue

            if line.startswith('@@'):
                count_block()
                continue

            if line.startswith('+'):
                added_lines += 1
                continue

            if line.startswith('-'):
                deleted_lines += 1
                continue

            count_block()

        count_block()
        return changes

    @staticmethod
    def _get_status_kind(sample_name, base_samples, current_samples):
        if sample_name not in base_samples:
            return 'added'
        if sample_name not in current_samples:
            return 'deleted'
        return 'modified'

    @staticmethod
    def _reset_local_added_sample(project_name, project_id, sample_name):
        reply = grew_request(
            "getConll",
            data={"project_id": project_name, "sample_id": sample_name},
        )
        sample_tree = SampleExportService.serve_sample_trees(reply.get("data", {}))
        sample_users = {
            user_id
            for sentence in sample_tree.values()
            for user_id in sentence.get("conlls", {})
        }

        if USERNAME not in sample_users:
            return

        if sample_users == {USERNAME}:
            GrewService.delete_samples(project_name, [sample_name])
            SampleService.SampleBlindAnnotationLevelService.delete_by_sample_name(project_id, sample_name)
            return

        grew_request(
            "eraseGraphs",
            {
                "project_id": project_name,
                "sample_id": sample_name,
                "sent_ids": "[]",
                "user_id": USERNAME,
            },
        )

    @staticmethod
    def get_modified_samples(project_name):
        project, sync_repository, github_access_token = GithubCommitStatusService._get_sync_context(project_name)
        current_samples = {sample["name"] for sample in GrewService.get_samples(project_name)}
        
        all_staged_info = {}
        for sample_name in current_samples:
            staging_info = StagingService.get_staged_status_by_sample(project.id, sample_name)
            if staging_info:
                all_staged_info[sample_name] = staging_info
        
        # users who have staged trees
        staged_users = set()
        for sample_name, staging_info in all_staged_info.items():
            for sent_id, trees_info in staging_info.items():
                for tree_user_id in trees_info.keys():
                    staged_users.add(tree_user_id)
        
        comparison_users = staged_users if staged_users else {USERNAME}
        
        all_users_to_compare = (staged_users | {USERNAME}) if staged_users else {USERNAME}
        current_contents = {}
        
        for user_to_compare in all_users_to_compare:
            user_contents = GrewService.get_samples_with_string_contents_as_dict(project_name, sorted(current_samples), user_to_compare) if current_samples else {}
            current_contents.update(user_contents)
        
        base_samples = GithubCommitStatusService._list_base_samples(
            github_access_token,
            sync_repository.repository_name,
            sync_repository.base_sha,
        )

        modified_samples = []
        for sample_name in sorted(base_samples.union(current_samples)):
            base_content = GithubCommitStatusService._get_base_sample_content(
                github_access_token,
                sync_repository.repository_name,
                sync_repository.base_sha,
                sample_name,
            )
            current_content = current_contents.get(sample_name, "")
            if base_content == current_content:
                continue

            diff_string = GithubCommitStatusService._build_diff(base_content, current_content, sample_name)
            
            staging_info = all_staged_info.get(sample_name, {})
            
            staged_list = []
            for sent_id, trees_info in staging_info.items():
                for tree_user_id, stage_data in trees_info.items():
                    staged_list.append({
                        "sent_id": sent_id,
                        "tree_user_id": tree_user_id,
                        "staged_by": stage_data.get("staged_by"),
                        "staged_at": stage_data.get("staged_at")
                    })
            
            modified_samples.append({
                "sample_name": sample_name,
                "changes_number": GithubCommitStatusService._count_changed_lines(diff_string),
                "status": GithubCommitStatusService._get_status_kind(sample_name, base_samples, current_samples),
                "diff": diff_string,
                "staged_list": staged_list,
            })

        return modified_samples

    @staticmethod
    def reset_samples(project_name, modified_samples):
        project, sync_repository, github_access_token = GithubCommitStatusService._get_sync_context(project_name)
        current_samples = {sample["name"] for sample in GrewService.get_samples(project_name)}

        for sample_name in modified_samples:
            file_metadata = GithubService.get_file_content_by_commit_sha(
                github_access_token,
                sync_repository.repository_name,
                sample_name + CONLL,
                sync_repository.base_sha,
            )
            download_url = file_metadata.get("download_url")

            if not download_url:
                if sample_name in current_samples:
                    GithubCommitStatusService._reset_local_added_sample(project_name, project.id, sample_name)
                continue

            file_name = sample_name + "_reset.conllu"
            path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
            content = requests.get(download_url).text
            with open(path_file, "w", encoding="utf-8") as file:
                file.write(content)

            SampleService.add_or_replace_userid(path_file, USERNAME)
            SampleService.add_or_keep_timestamps(path_file)

            if sample_name not in current_samples:
                GrewService.create_samples(project_name, [sample_name])

            with open(path_file, "rb") as file_to_save:
                GrewService.save_sample(project_name, sample_name, file_to_save)

            os.remove(path_file)

class GithubService:
    """
        This class concerns all methods that deal with github API
        Here is the link of the documentation of the endpoints used in the following  methods
        https://docs.github.com/en/rest/git
    """
    @staticmethod    
    def base_header(access_token):
        """Base header is key-value pair that is used to send requests to github api

        Args:
            access_token (str): access token generated after loggin with github

        Returns:
           authorization dict(str, str)
        """
        return {"Authorization": "bearer " + access_token}
    
    @staticmethod
    def get_user_email(access_token) -> str:
        """Afte

        Args:
            access_token (_type_): _description_

        Returns:
            str: _description_
        """
        url = "https://api.github.com/user/emails"
        headers =  GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        return data[0].get("email")
    
    @staticmethod    
    def get_repositories(access_token):
        """
            List user repositories, the repositories are paginated 
            100 repos per page

        Args:
            access_token (str)
        Returns:
            list_repos: list of {"name": str, "owner_name": str, "owner_avatar": str}
        """
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
            repository = {
               "name": repo.get("full_name"),
               "owner_name": repo.get("owner").get("login"),
               "owner_avatar": repo.get("owner").get("avatar_url"),
            }
            repositories.append(repository) 
        return repositories 

    @staticmethod
    def list_repository_branches(access_token, full_name) -> List[str]:
        """List of repository branches, without dependbot branches

        Args:
            access_token (str)
            full_name (str): full_name is "github_username/repository_name"

        Returns:
            List[str]: list of branches
        """
        url = "https://api.github.com/repos/{}/branches".format(full_name)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers ) 
        data = response.json()
        return [branch.get("name") for branch in data if "dependabot" not in branch.get("name")]

    @staticmethod    
    def get_repository_files_of_branch(access_token, full_name, branch):
        """Get list of files of specific repo in specific branch

        Args:
            access_token (str)
            full_name (str)
            branch (str)

        Returns:
            list_files(List[files])
        """
        url = "https://api.github.com/repos/{}/contents/?ref={}".format(full_name, branch)
        headers = GithubService.base_header(access_token)
        response = requests.get(url , headers=headers)
        data = response.json()
        return data
   
    @staticmethod   
    def get_file_sha(access_token, full_name, file_path, branch):
        """Get file sha hash of the last of commit of specific file

        Args:
            access_token (str)
            full_name (str)
            file_path (str)
            branch (_type_)

        Returns:
            sha(str)
        """
        url = "https://api.github.com/repos/{}/contents/{}?ref={}".format(full_name, file_path, branch)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("sha")
    
    @staticmethod
    def get_sha_base_tree(access_token, full_name, branch):
        """Get the hash of the tree object of the github repo

        Args:
            access_token (str)
            full_name (str)
            branch (str)

        Returns:
            sha(str)
        """
        url = "https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch)
        headers =  GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        try:
            return data.get("object").get("sha")
        except:
            abort(400, "The Github repository doesn't exist anymore") 

    @staticmethod
    def get_commit_tree_sha(access_token, full_name, commit_sha):
        url = "https://api.github.com/repos/{}/git/commits/{}".format(full_name, commit_sha)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        tree = data.get("tree", {})
        return tree.get("sha")
              
    @staticmethod
    def create_blob_for_updated_file(access_token, full_name, content):
        """Git blob is the object used to store the content of each file in a repository 

        Args:
            access_token (str)
            full_name (str)
            content (str)

        Returns:
            blob_sha(str)
        """
        data = {"content": content, "encoding": "utf-8"}
        url = "https://api.github.com/repos/{}/git/blobs".format(full_name)
        headers = GithubService.base_header(access_token)
        response = requests.post(url, headers=headers , data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
    
    @staticmethod
    def download_github_repository(access_token, full_name, branch):
        """Download a github repository in tmp.zip file

        Args:
            access_token (str)
            full_name (str)
            branch (str)

        Returns:
            path_file(str)
        """
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
    def create_new_branch_arborator(access_token, full_name, branch_to_create, default_branch):
        """Create new branch to be synchronized with AG

        Args:
            access_token (str)
            full_name (str)
            branch_to_create (str)
            default_branch (str)

        Returns:
            response
        """
        url = "https://api.github.com/repos/{}/git/refs".format(full_name)
        headers =  GithubService.base_header(access_token)
        sha = GithubService.get_sha_base_tree(access_token, full_name, default_branch)
        data = {
            "ref": "refs/heads/{}".format(branch_to_create),
            "sha": sha
        }
        response = requests.post(url, headers=headers, data = json.dumps(data))
        return response.json()

    @staticmethod
    def extract_repository(file_path):
        """
        extract the zip folder that compress github repository we extract files with specefic size 

        Args:
            file_path (str)
        """
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
        """check if file is large if it's bigger then 13MB

        Args:
            file_path (str)
        """
        file_size = (os.stat(file_path).st_size)/(1024*1024)
        if file_size > 13:
            abort(413, "it contains a large file")
    
    @staticmethod 
    def create_tree(access_token, full_name, updated_samples, project_name, base_tree):
        """
            In order to commit changes we need to create a tree which that contains 
            blobs of modified files 

        Args:
            access_token (str)
            full_name (str)
            updated_samples (str) list of modified samples
            project_name (str)
            base_tree (str): the sha of an existing tree object which will be used as the base for the new tree

        Returns:
            new_base_sha(str)
        """
        tree = []
        current_samples = {sample["name"] for sample in GrewService.get_samples(project_name)}
        existing_samples = [sample_name for sample_name in updated_samples if sample_name in current_samples]
        sample_names, sample_content_files = GrewService.get_samples_with_string_contents(project_name, existing_samples)
        for sample_name, sample in zip(sample_names, sample_content_files):
            content = sample.get(USERNAME)
            sha = GithubService.create_blob_for_updated_file(access_token, full_name, content)
            blob = {"path": sample_name + CONLL, "mode": "100644", "type": "blob", "sha": sha}
            tree.append(blob)

        deleted_samples = [sample_name for sample_name in updated_samples if sample_name not in current_samples]
        for sample_name in deleted_samples:
            tree.append({"path": sample_name + CONLL, "mode": "100644", "type": "blob", "sha": None})

        url = "https://api.github.com/repos/{}/git/trees".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {"tree": tree, "base_tree": base_tree}

        response = requests.post(url, headers=headers, data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
    
    @staticmethod
    def create_commit(access_token, tree, parent, message, full_name):
        """create a commit

        Args:
            access_token (str)
            tree (str)
            parent (str): base_tree sha
            message (str): commit message
            full_name (str)

        Returns:
            tree_sha(str): sha of the new tree
        """
        url = "https://api.github.com/repos/{}/git/commits".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {"tree": tree, "parents": [parent], "message": message}
        response = requests.post(url, headers=headers, data = json.dumps(data) )
        data = response.json()
        return data.get("sha")
    
    @staticmethod
    def update_sha(access_token, full_name, branch, sha):
        """_summary_

        Args:
            access_token (str)
            full_name (str)
            branch (str)
            sha (str): new sha
        """
        url = "https://api.github.com/repos/{}/git/refs/heads/{}".format(full_name, branch)
        headers = GithubService.base_header(access_token)
        data = {"sha": sha}

        response = requests.patch(url, headers=headers,  data= json.dumps(data))
        return response
    
    @staticmethod
    def compare_two_commits(access_token, full_name, previous_commit, new_commit):
        """Compare between commits in order to get the modified to use it later for the pull

        Args:
            access_token (str)
            full_name (str)
            previous_commit (str): sha of actual base tree in AG
            new_commit (str): the new base tree sha

        Returns:
            list_files: list of updated files {"filename": str, "status": 'modified' | 'added' | 'removed' }
        """
        url = 'https://api.github.com/repos/{}/compare/{}...{}'.format(full_name, previous_commit, new_commit)
        headers = GithubService.base_header(access_token)
        response = requests.get(url, headers=headers)
        data = response.json()
        modified_files = data.get('files')
        return modified_files
    
    @staticmethod
    def get_file_content_by_commit_sha(access_token, full_name, file_path, sha):
        """Get content of a file in repo based on the commit sha

        Args:
            access_token (str)
            full_name (str)
            file_path (str)
            sha (str)
        """
        url = "https://api.github.com/repos/{}/contents/{}?ref={}".format(full_name, file_path, sha)
        headers = GithubService.base_header(access_token)

        response = requests.get(url, headers=headers)
        data = response.json()
        return data
    
    @staticmethod
    def create_pull_request(access_token, full_name, username, arborator_branch, branch, title):
        """ Create a pull request

        Args:
            access_token (str)
            full_name (str)
            username (str)
            arborator_branch (str)
            branch (str)
            title (str): the title of the pull request
        """
        url = "https://api.github.com/repos/{}/pulls".format(full_name)
        headers = GithubService.base_header(access_token)
        head = username + ":" + arborator_branch
        data = {"title": title, "head": head, "base": branch}
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if not response:
            error = response.json()['errors'][0].get("message") 
            abort(422, error)
    
    @staticmethod
    def delete_file(access_token, full_name, file_path, branch):
        """ Delete file 

        Args:
            access_token (str)
            full_name (str)
            file_path (str)
            branch (str)
        """
        url = "https://api.github.com/repos/{}/contents/{}".format(full_name, file_path)
        headers = GithubService.base_header(access_token)
        sha = GithubService.get_file_sha(access_token, full_name, file_path, branch)
        data = {"sha": sha, "message": "file deleted from github", "branch": branch}

        response = requests.delete(url, headers=headers , data=json.dumps(data))
        return response

    @staticmethod
    def rename_file_in_github_repo(
        access_token,
        full_name,
        old_file_path,
        new_file_path,
        branch,
    ):
        """Rename a file by reusing the existing blob in a single git commit."""
        if old_file_path == new_file_path:
            return GithubService.get_sha_base_tree(access_token, full_name, branch)

        parent_commit_sha = GithubService.get_sha_base_tree(access_token, full_name, branch)
        base_tree_sha = GithubService.get_commit_tree_sha(access_token, full_name, parent_commit_sha)
        file_sha = GithubService.get_file_sha(access_token, full_name, old_file_path, branch)

        url = "https://api.github.com/repos/{}/git/trees".format(full_name)
        headers = GithubService.base_header(access_token)
        data = {
            "base_tree": base_tree_sha,
            "tree": [
                {"path": old_file_path, "mode": "100644", "type": "blob", "sha": None},
                {"path": new_file_path, "mode": "100644", "type": "blob", "sha": file_sha},
            ],
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        new_tree_sha = response.json().get("sha")

        commit_sha = GithubService.create_commit(
            access_token,
            new_tree_sha,
            parent_commit_sha,
            "Rename {} to {}".format(old_file_path, new_file_path),
            full_name,
        )
        update_response = GithubService.update_sha(access_token, full_name, branch, commit_sha)
        update_response.raise_for_status()
        return commit_sha

    @staticmethod
    def is_repository_branch_empty(access_token, full_name):
        """Check if a GitHub repository has no branches (is empty)
        
        Args:
            access_token (str)
            full_name (str): owner/repo
            
        Returns:
            bool: True if repository has no branches
        """
        try:
            branches = GithubService.list_repository_branches(access_token, full_name)
            return len(branches) == 0
        except:
            return False

    @staticmethod
    def create_initial_empty_commit(access_token, full_name, branch_name="main"):
        """Create an initial commit and branch for an empty repository by creating a README file
        
        Args:
            access_token (str)
            full_name (str): owner/repo
            branch_name (str): name of the branch to create (default: main)
            
        Returns:
            str: the commit SHA
        """
        url = "https://api.github.com/repos/{}/contents/README.md".format(full_name)
        headers = GithubService.base_header(access_token)
        content = base64.b64encode(b"").decode('utf-8') # empty content for the README file
        data = {
            "message": "Initial commit",
            "content": content,
            "branch": branch_name
        }
        response = requests.put(url, headers=headers, data=json.dumps(data))

        result = response.json()
        return result.get("commit").get("sha")


class GithubWorkflowService:

    @staticmethod
    def import_files_from_github(full_name, project_name, branch, branch_syn):
        """Import files from github:
            - Get repository files names of specific branch 
            - In order to not download file by file we import directly repo in zip file
            - We extract the zip file and create new samples from the extracted file
            - Create new branch if user choosed to use branch dedicated for the sync

        Args:
            full_name (str)
            project_name (str)
            branch (str): branch used for the import
            branch_syn (str): branch used for the synchronization
        """
        access_token = UserService.get_by_id(current_user.id).github_access_token
        repository_files = GithubService.get_repository_files_of_branch(access_token, full_name, branch)
        conll_files = [file.get("name") for file in repository_files if extension.search(file.get('name'))]

        tmp_zip_file = GithubService.download_github_repository(access_token, full_name, branch)
        GithubService.extract_repository(tmp_zip_file)
        GithubWorkflowService.clone_github_repository(conll_files, project_name)
        if branch_syn != branch:  
            GithubService.create_new_branch_arborator(access_token, full_name, branch_syn, branch)
        
    @staticmethod 
    def clone_github_repository(files, project_name):
        """
            Clone github repository means create new samples from the files 
            of sync repo

        Args:
            files (List[str])
            project_name (str)
        """
        for file in files:
            path_file = os.path.join(Config.UPLOAD_FOLDER, file)
            sample_name = file.split(CONLL)[0]
            GithubWorkflowService.create_sample(sample_name, path_file, project_name)
            os.remove(path_file)

    @staticmethod
    def create_sample(sample_name, path_file, project_name):
        """Create new sample

        Args:
            sample_name (str)
            path_file (str)
            project_name (str)
        """
        if not SampleService.check_sentences_without_sent_ids(path_file):
            SampleService.add_new_sent_ids(path_file, sample_name)

        SampleService.check_duplicate_sent_id(path_file, sample_name)
        SampleService.check_if_file_has_user_ids(path_file, sample_name)
        SampleService.add_or_replace_userid(path_file, USERNAME)
        SampleService.add_or_keep_timestamps(path_file)
        
        grew_samples = GrewService.get_samples(project_name)
        samples_names = [sa["name"] for sa in grew_samples]
        if sample_name not in samples_names:
            GrewService.create_samples(project_name, [sample_name])
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)

    @staticmethod
    def commit_changes(updated_samples, project_name, message):
        """Commit changes 
        Args:
            updated_samples (List[str]):modified samples
            project_name (int)
            message (str): commit message

        Returns:
            sha(str): new sha after the commit
        """
        access_token = UserService.get_by_id(current_user.id).github_access_token
        project = ProjectService.get_by_name(project_name)
        sync_repository = GithubRepositoryService.get_by_project_id(project.id)

        parent = GithubService.get_sha_base_tree(access_token, sync_repository.repository_name, sync_repository.branch)
        tree = GithubService.create_tree(access_token, sync_repository.repository_name, updated_samples, project_name, parent)
        sha = GithubService.create_commit(access_token, tree, parent, message, sync_repository.repository_name)
        response = GithubService.update_sha(access_token, sync_repository.repository_name, sync_repository.branch, sha)
        data = response.json()
        return data.get("object").get("sha")
    
    @staticmethod
    def check_pull(access_token, project_name):
        """Check if there is changes to pull, if the base_tree sha of AG is different from base_tree in Github

        Args:
            access_token (str)
            project_name (str)

        Returns:
            boolean
        """
        project = ProjectService.get_by_name(project_name)
        sync_repository = GithubRepositoryService.get_by_project_id(project.id)
        base_tree = GithubService.get_sha_base_tree(access_token, sync_repository.repository_name, sync_repository.branch)
        return sync_repository.base_sha != base_tree
    
    @staticmethod
    def preview_pull_changes(project_name):
        """Preview which files would be modified by pull without actually pulling
        
        Args:
            project_name (str)
        
        Returns:
            list: List of sample names that would be modified, added, or removed by the pull
        """
        project = ProjectService.get_by_name(project_name)
        sync_repository = GithubRepositoryService.get_by_project_id(project.id)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token
        
        base_tree = GithubService.get_sha_base_tree(github_access_token, sync_repository.repository_name, sync_repository.branch)
        modified_files = GithubService.compare_two_commits(github_access_token, sync_repository.repository_name, sync_repository.base_sha, base_tree)
        
        affected_samples = []
        for file in modified_files:
            if extension.search(file.get('filename')):
                sample_name = file.get("filename").split(".conllu")[0]
                affected_samples.append({
                    "sample_name": sample_name,
                    "status": file.get("status")
                })
        
        return affected_samples
    
    @staticmethod 
    def pull_changes(project_name):
        """Pull changes:
            - compare between two commits
            - get the modified files 
            - from every status:
                - added: create new sample from new added file 
                - modified: pull changes 
                - removed: deleted the sample of the removed file from AG project

        Args:
            project_name (str)
        """
        project = ProjectService.get_by_name(project_name)
        sync_repository = GithubRepositoryService.get_by_project_id(project.id)
        github_access_token = UserService.get_by_id(current_user.id).github_access_token

        base_tree = GithubService.get_sha_base_tree(github_access_token, sync_repository.repository_name, sync_repository.branch)
        modified_files = GithubService.compare_two_commits(github_access_token, sync_repository.repository_name, sync_repository.base_sha, base_tree)
        for file in modified_files:
            if extension.search(file.get('filename')):
                sample_name = file.get("filename").split(".conllu")[0]
                file_content= GithubService.get_file_content_by_commit_sha(github_access_token, sync_repository.repository_name, file.get("filename"), base_tree)
                download_url = file_content.get("download_url")
                if file.get("status") == "renamed":
                    previous_filename = file.get("previous_filename")
                    previous_sample_name = previous_filename.split(".conllu")[0]
                    GithubWorkflowService.delete_sample_from_project(project_name, previous_sample_name)
                    GithubWorkflowService.create_sample_from_github_file(sample_name, download_url, project_name)
                if file.get("status") == "added":
                    GithubWorkflowService.create_sample_from_github_file(sample_name, download_url, project_name)
                if file.get("status") == "modified":
                    GithubWorkflowService.pull_change_existing_sample(project_name, sample_name, download_url)
                if file.get("status") == "removed":
                    GithubWorkflowService.delete_sample_from_project(project_name, sample_name)
        GithubRepositoryService.update_sha(project.id, base_tree)

    @staticmethod
    def create_sample_from_github_file(file, download_url, project_name):
        """Create new sample after a pull using the download url

        Args:
            file (str): sample name
            download_url (str)
            project_name (str)
        """
        sample_name, path_file =  GithubWorkflowService.download_github_file_content(file, download_url)
        GithubWorkflowService.create_sample(sample_name, path_file, project_name)
        os.remove(path_file)

    @staticmethod
    def download_github_file_content(file_name, download_url):
        """Download modified file and save it in AG

        Args:
            file_name (str)
            download_url (str)

        Returns:
            sample_name, path_file(Tuple(str, str))
        """
        sample_name = file_name.split(CONLL)[0]
        raw_content = requests.get(download_url)
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        file = open(path_file, "w", encoding='utf-8')
        file.write(raw_content.text)
        file.close()
        return sample_name, path_file
    
    @staticmethod
    def pull_change_existing_sample(project_name, sample_name, download_url):
        """pull changes of an existing file 

        Args:
            project_name (str)
            sample_name (str)
            download_url (str)
        """
        content = requests.get(download_url).text 
        file_name = sample_name + "_modified.conllu"
        path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
        with open(path_file, "w", encoding='utf-8') as file:
            file.write(content)

        SampleService.add_or_replace_userid(path_file, USERNAME)
        SampleService.add_or_keep_timestamps(path_file)
        
        with open(path_file, "rb") as file_to_save:
            GrewService.save_sample(project_name, sample_name, file_to_save)
        os.remove(path_file)
        
        conlls_strings = SampleService.split_conll_string_to_conlls_list(content)
        reply = grew_request("getConll", data={"project_id": project_name, "sample_id": sample_name},)
        sample_trees =SampleExportService.serve_sample_trees(reply.get("data", {}))
        modified_sentences = []
        for conll in conlls_strings:
            for line in conll.rstrip().split("\n"):
                if "# sent_id = " in line:
                    sent_id = line.split("# sent_id = ")[-1] 
                    modified_sentences.append(sent_id)
        deleted_sentences = [sent_id for sent_id in sample_trees.keys() if sent_id not in modified_sentences]
        if deleted_sentences:
            data = { "project_id": project_name, "sample_id": sample_name, "sent_ids": json.dumps(deleted_sentences), "user_id": USERNAME }
            grew_request("eraseGraphs", data)
        
    @staticmethod
    def delete_files_from_github(access_token, project_name, sample_names):
        """delete files from github

        Args:
            access_token (str)
            project_name (str)
            sample_names (List[str])
        """
        for sample_name in sample_names:
            file_path = sample_name + CONLL
            project_id = ProjectService.get_by_name(project_name).id
            repository = GithubRepositoryService.get_by_project_id(project_id)
        
            GithubService.delete_file(access_token, repository.repository_name, file_path, repository.branch)
            new_base_tree_sha = GithubService.get_sha_base_tree(access_token, repository.repository_name, repository.branch)
            GithubRepositoryService.update_sha(project_id, new_base_tree_sha)
    
    @staticmethod
    def delete_sample_from_project(project_name, sample_name):
        project = ProjectService.get_by_name(project_name)
        sample_ids = [sample_name] 
        GrewService.delete_samples(project_name, sample_ids)
        SampleService.SampleBlindAnnotationLevelService.delete_by_sample_name(project.id, sample_name)


