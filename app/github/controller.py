from flask_restx import Namespace, Resource, reqparse
from ..projects.service import ProjectService
from ..user.service import UserService
from .service import GithubRepositoryService, GithubService
from flask_login import current_user

api = Namespace("Github", description="Endpoints for dealing with github repositories") 



@api.route("/<string:projectName>/me/github")
class GithubRepository(Resource):
    def get(self, projectName):
        return GithubService.get_repositories(UserService.get_by_id(current_user.id).github_access_token)

@api.route("/<string:projectName>/github-repository")
class SynchronizedGithubRepositoryController(Resource):
    def get(self, project_name: str, user_id: str):
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        return GithubRepositoryService.get_github_repository_per_user(user_id, project.id)
    
    def post(self, project_name: str, user_id: str):
        parser = reqparse.RequestParser()
        parser.add_argument(name="repositoryName")
        args = parser.parse_args()
        repository_name = args.get("repositoryName")

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        GithubRepositoryService.synchronize_github_repository(user_id, project.id, repository_name)

        return {"status": "success"}

