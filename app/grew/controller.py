import os 

from flask import abort, request, Response
from flask_login import current_user
from flask_restx import Namespace, Resource

from app.config import Config
from app.projects.service import LastAccessService, ProjectService
from app.github.service import GithubCommitStatusService, GithubRepositoryService
from app.utils.grew_utils import GrewService, SampleExportService



api = Namespace(
    "Grew", description="Endpoints for dealing with samples of project"
)  # noqa


@api.route("/<string:project_name>/apply-rule")
class ApplyRuleResource(Resource):
    def post(self, project_name: str):

        project =ProjectService.get_by_name(project_name)
        ProjectService.check_if_freezed(project)
        
        args = request.get_json()
        data = args.get("data")

        for sample_name, sample_trees in data.items():
            new_conll = ''
            for tree in sample_trees.values():
                
                if 'validated' in tree["conlls"].keys() and GithubRepositoryService.get_by_project_id(project.id):
                    GithubCommitStatusService.update_changes(project.id, sample_name)
                    
                for user in tree["conlls"]:
                    new_conll += tree["conlls"][user] + "\n\n"
                    
            file_name = sample_name + "_modified.conllu"
            path_file = os.path.join(Config.UPLOAD_FOLDER, file_name)
            
            with open(path_file, "w") as file:
                file.write(new_conll)
                
            with open(path_file, "rb") as file_to_save:
                GrewService.save_sample(project_name, sample_name, file_to_save)
            
            os.remove(path_file)    
                
        LastAccessService.update_last_access_per_user_and_project(current_user.id, project_name, "write")


@api.route("/<string:project_name>/search")
class SearchResource(Resource):
    "Search"
    def post(self, project_name: str):

        args = request.get_json()
        pattern = args.get("pattern")
        trees_type = args.get("userType") 
        sample_ids = args.get("sampleIds")
        other_user = args.get("otherUser")
        
        user_type = 'all' if trees_type == 'pending' else trees_type
        if not sample_ids: 
            sample_ids = [sample["name"] for sample in GrewService.get_samples(project_name)]

        response = GrewService.search_request_in_graphs(project_name, pattern, user_type, other_user)
        
        if response["status"] != "OK":
            abort(400)
        
        search_results = GrewService.post_process_grew_results(response["data"], sample_ids, trees_type)
        return search_results

@api.route("/<string:project_name>/try-package")
class TryPackageResource(Resource):
    "rewrite"
    def post(self, project_name: str):
    
        args = request.get_json()
        
        package = args.get("query")
        user_type = args.get("userType")
        other_user = args.get("otherUser")
        sample_ids = args.get("sampleIds", None)
        if not sample_ids: 
            sample_ids = []
            
        reply = GrewService.try_package(project_name, package, sample_ids, user_type, other_user)
        if reply["status"] != "OK":
            abort(400)
        trees = {}
        for m in reply["data"]:
            if m["user_id"] == "":
                abort(409)
            trees = GrewService.format_trees_new(m, trees, is_package=True)
        return trees

@api.route("/<string:project_name>/relation-table")
class RelationTableResource(Resource):
    def post(self, project_name):

        args = request.get_json()
        sample_ids = args.get("sampleIds")
        table_type = args.get("tableType")
        other_user = args.get("otherUser")
        
        reply = GrewService.get_relation_table(project_name, sample_ids, table_type, other_user)
        if reply["status"] != "OK":
            abort(400)
        data = reply.get("data")    
        return data
    
@api.route("/<string:project_name>/export-results")
class ExportGrewResultsResource(Resource):
    
    def post(self, project_name: str):
        
        args = request.get_json()
        search_results = args.get("searchResults")
        users = args.get("users")
        
        trees = {}
        sample_content_files = []
        samples_names = []
        
        for sample_name, results in search_results.items():
            samples_names.append(sample_name)
            trees = {}
            for sent_id, tree in results.items():
                trees[sent_id] = tree['conlls']
            
            sample_tree_nots_noui = SampleExportService.serve_sample_trees(trees, timestamps=False, user_ids=False)
            sample_content = SampleExportService.sample_tree_to_content_file(sample_tree_nots_noui)
                
            sample_content_files.append(sample_content)

        zip_file = SampleExportService.content_files_to_zip(
            samples_names, sample_content_files, users
        )

        resp = Response(
            zip_file,
            status=200,
            mimetype="application/zip",
            headers={
                "Content-Disposition": "attachment;filename=dump.{}.zip".format(project_name)
            },
        )
        return resp
        
            