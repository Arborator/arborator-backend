import datetime
import operator
from collections import defaultdict

from flask import request
from flask_restx import Namespace, Resource
from flask_accepts.decorators.decorators import responds

from app.user.service import UserService
from app.projects.service import LastAccessService

from app.utils.grew_utils import GrewService
from .interface import StatProjectInterface
from .schema import StatProjectSchema

api = Namespace("statistics", description="Endpoints for dealing with statistics of project")

@api.route('/<string:project_name>/statistics')
class StaticsProjectResource(Resource):
    
    @responds(schema=StatProjectSchema, api=api)
    def get(self, project_name):
        """Get project statistics"""
        project_stats: StatProjectInterface = {}
        grew_projects = GrewService.get_projects()
        project = [project for project in grew_projects if project["name"] == project_name][0]
        
        project_stats["users"] = project["users"]
        project_stats["samples_number"] = project["number_samples"]
        project_stats["trees_number"] = project["number_trees"]
        project_stats["tokens_number"] = project["number_tokens"]
        project_stats["sentences_number"] = project["number_sentences"]
        
        grew_samples = GrewService.get_samples(project_name)
        users = defaultdict(int)
        for sample in grew_samples:
            for key, value in sample["tree_by_user"].items():
                if key != 'validated':
                    users[key] += value   
        if users.items():     
            max_user_trees = max(users.items(), key=operator.itemgetter(1))
            if UserService.get_by_username(max_user_trees[0]) != None:
                project_stats["top_user"] = {
                    "username": max_user_trees[0],
                    "trees_number": max_user_trees[1],
                    "user_avatar": UserService.get_by_username(max_user_trees[0]).picture_url
                }       
    
        project_last_read, project_last_write = LastAccessService.get_project_last_access(project_name)
        now = datetime.datetime.now().timestamp()
        project_stats["last_write"] = {
            "last_write": project_last_write - now,
            "last_write_username": LastAccessService.get_user_by_last_access_and_project(
            project_name, project_last_write, "write")
        }
        project_stats["last_read"] = {
            "last_read": project_last_read - now,
            "last_read_username": LastAccessService.get_user_by_last_access_and_project(
            project_name, project_last_read, "read")
        }
        
        return project_stats
        
              
        