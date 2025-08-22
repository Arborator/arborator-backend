import os
import base64
import datetime
from typing import Dict, List

from flask import abort, current_app
from flask_login import current_user
from sqlalchemy import desc

from app import db
from .interface import ProjectInterface, ProjectExtendedInterface
from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature, LastAccess
from ..user.service import UserService

class ProjectService:
    """Class deals with the methods that concerns project entity"""
    
    @staticmethod
    def get_all() -> List[Project]:
        """Get all list of project in db ordered by last access value

        Returns:
            List[Project]
        """
        return Project.query.join(LastAccess).order_by(desc(LastAccess.last_read)).all()

    @staticmethod
    def create(new_attrs: ProjectInterface) -> Project:
        """Create new project in db

        Args:
            new_attrs (ProjectInterface): dict of project attributes

        Returns:
            Project: new project entity
        """
        new_project = Project(**new_attrs)
        db.session.add(new_project)
        db.session.commit()
        return new_project

    @staticmethod
    def get_by_name(project_name: str) -> Project:
        """Get project entity by its name

        Args:
            project_name (str) 

        Returns:
            Project: project entity
        """
        
        return Project.query.filter(Project.project_name == project_name).first()

    @staticmethod
    def update(project: Project, changes) -> Project:
        """update project propreties

        Args:
            project (Project) 
            changes (ProjectInterface): dict of propreties to be updated

        Returns:
            Project: updated project entity
        """
        
        project.update(changes)
        db.session.commit()
        return project

    @staticmethod
    def delete_by_name(project_name: str):
        """Delete project by its name

        Args:
            project_name (str)

        Returns:
            prject_name: returns project name if the project exists in db else empty string 
        """
        project = Project.query.filter(
            Project.project_name == project_name).first()
        if project:
            db.session.delete(project)
            db.session.commit()
            return project_name
        else:
            return ""

    @staticmethod
    def check_if_project_exist(project: Project) -> None:
        """check if the project exist in database

        Args:
            project (Project)
        """
        if not project:
            abort(404, "There was no such project stored on arborator backend")
    
    @staticmethod 
    def check_if_freezed(project: Project) -> None:
        """
            Freezed projects are project that can't be edited
            by the user, only the owner of the project who can
            freeze the project, so if the project is freezed no one 
            have access to the samples or features that update data

        Args:
            project (Project)
        """
        if project.freezed and (not current_user.is_authenticated or ProjectAccessService.get_admins(project.id)[0] != current_user.username): 
            abort(403, "You can't access the project when it's freezed")
            
    @staticmethod
    def get_project_image(image_path: str) -> str:
        """
            Get the  project image from the project image folder 
            and send it to the frontend in base64 coding format

        Args:
            image_path (str): path of the image in db

        Returns:
            str: string the contains the encoding of the image
        """
        if image_path:
            image_path = os.path.join(current_app.config["PROJECT_IMAGE_FOLDER"], image_path)
            if os.path.exists(image_path):
                with open(image_path, 'rb') as file:
                    image_data = base64.b64encode(file.read()).decode('utf-8')
                    if len(image_path.split(".")) > 1:
                        project_image = 'data:image/{};base64,{}'.format(image_path.split(".")[1], image_data)
                        return project_image
     
    @staticmethod
    def get_projects_info(db_projects, grew_projects, page, total_projects, projects_type):
        
        """
            Get project information, since some of the projects information 
            are stored in the db and in grew server so we have to send both information to the frontend
        Args:
            db_projects(List[Project]): list of the project in the db
            grew_projects(List[GrewProject])
            page(int)
            total_projects(int): number of projects per page or -1 if we want to get all projects
            projects_type(str): my_projects | all_projects | other_projects | old_projects | my_old_projects
        Returns:
            projects_extended_list(List[ProjectExtendedInterface]): union of db_projects and grew_projects with different info
        """
        projects: List[ProjectExtendedInterface] = []
        grew_projects_names = [project["name"] for project in grew_projects]
        db_projects_names = [project.project_name for project in db_projects]

        common = [project for project in db_projects_names if project in grew_projects_names]
   
        filtered_common = [project for project in  common if (
            ProjectService.filter_project_by_type(ProjectService.get_by_name(project), projects_type) and
            ProjectAccessService.check_project_access(ProjectService.get_by_name(project).visibility, ProjectService.get_by_name(project).id)
        )]
        if total_projects != -1:
            start_index = (int(page) - 1) * total_projects
            end_index = start_index + total_projects
            paginated_common = filtered_common[start_index:end_index]
            total_pages = len(filtered_common) // total_projects + 1
        else:
            paginated_common = filtered_common
            total_pages = 1
        for project_name in paginated_common:
            grew_project = next(project for project in grew_projects if project["name"] == project_name)
            project = ProjectService.get_by_name(project_name)
           
            (
                project.admins,
                project.validators,
                project.annotators,
                project.guests,
            ) = ProjectAccessService.get_all(project.id)
            
            project.owner = project.admins[0] if project.admins else ''
            project.owner_avatar_url = UserService.get_by_username(project.admins[0]).picture_url if project.admins else ''
            project.contact_owner = UserService.get_by_username(project.admins[0]).email if project.admins else ''
            project.sync_github = project.github_repository.repository_name if project.github_repository else ''
            
            (last_access, last_write_access) = LastAccessService.get_project_last_access(project.project_name)
            now = datetime.datetime.now().timestamp()
            project.last_access = last_access - now
            project.last_write_access = last_write_access - now
            project_path = project.image
            project.image = ProjectService.get_project_image(project_path)
            
            project.users = grew_project["users"]
            project.number_sentences = grew_project["number_sentences"]
            project.number_samples = grew_project["number_samples"]
            project.number_tokens = grew_project["number_tokens"]
            project.number_trees = grew_project["number_trees"]            
        
            projects.append(project)
        return projects, total_pages
    
    @staticmethod
    def filter_project_by_name_or_language(name, languages):
        """
            Filter projects by name or language

        Args:
            name (str): project name
            languages (List[str]): project languages to filter 

        Returns:
            projects (List[Project]): list of projects
        """
        projects: List[Project] = Project.query.all()
        if name:
            projects = [project for project in projects if name.lower() in project.project_name.lower()]
        if languages is not None:
            projects = [project for project in projects if project.language in languages]
        return projects
    
    @staticmethod
    def filter_project_by_type(project, project_type):
        """filter project by type

        Args:
            project (ProjectExtendedInterface)
            project_type (str): my_projects | all_projects | other_projects | my_old_projects

        Returns:
            boolean
        """
        year = -3600 * 24 * 365
        if project_type == "my_projects":
            return ProjectAccessService.get_by_user_id(current_user.id, project.id) is not None
        elif project_type == "other_projects":
            return ProjectAccessService.get_by_user_id(current_user.id, project.id) is None
        elif project_type == "my_old_projects":
            last_access = LastAccessService.get_project_last_access(project.project_name)[0]
            return last_access - datetime.datetime.now().timestamp() < year
        else:
            return True

    @staticmethod
    def get_recent_projects(time_ago):
        """Get recent active project based on time_ago 

        Args:
            time_ago (number): number of days ago

        Returns:
            recent_projects(List[Project]): List of recent projects 
        """
        time_before = datetime.datetime.now() - datetime.timedelta(days=time_ago)
        timestamp = time_before.timestamp()
        recent_projects = (db.session.query(Project)
                           .join(LastAccess, Project.id == LastAccess.project_id)
                           .filter(LastAccess.last_write > timestamp, Project.blind_annotation_mode == 0)
                           .distinct()
            ).all()
        return recent_projects
                
class ProjectAccessService:
    """Class of methods that deal with project access entity"""
    
    @staticmethod
    def create(new_attrs) -> ProjectAccess:
        """Create new ProjectAccess entity

        Args:
            new_attrs: dict of project access attributes

        Returns:
            new_project_access: new project_access entity
        """
        new_project_access = ProjectAccess(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def update(project_access: ProjectAccess, changes):
        """update project access entity

        Args:
            project_access (ProjectAccess)
            changes (dict)

        Returns:
            project_access: updated project_access entity
        """
        project_access.update(changes)
        db.session.commit()
        return project_access

    @staticmethod
    def delete(user_id: str, project_id: int):
        """delete the access a user for a specific project

        Args:
            user_id (str)
            project_id (int)
        """
        project_access = ProjectAccess.query.filter_by(user_id=user_id, project_id=project_id).first()
        if project_access:
            db.session.delete(project_access)
            db.session.commit()

    @staticmethod
    def user_has_access_to_project(user_id):
        """
            Check if a user has access to any project in db
            to use it later to to redirect users to my projects page 
            either all projects when they logged in

        Args:
            user_id (str): 

        Returns:
            boolan
        """
        project_access = ProjectAccess.query.filter_by(user_id=user_id).all()
        if project_access:
            return True
        else:
            return False
        
    @staticmethod
    def get_by_user_id(user_id: str, project_id: int) -> ProjectAccess:
        """Get access by user and project

        Args:
            user_id (str)
            project_id (int)

        Returns:
            ProjectAccess
        """
        return ProjectAccess.query.filter_by(project_id=project_id, user_id=user_id).first()

    @staticmethod
    def get_admins(project_id: int) -> List[str]:
        """Get admins of a project

        Args:
            project_id (int)

        Returns:
            List[str]: list of admins usernames
        """
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id, access_level=3)
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_validators(project_id: int) -> List[str]:
        """Get validators of a project

        Args:
            project_id (int)

        Returns:
            List[str]: list of validators usernames
        """
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id, access_level=2)
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []
        
    @staticmethod
    def get_annotators(project_id: int) -> List[str]:
        """Get annotators of a project

        Args:
            project_id (int)

        Returns:
            List[str]: list of annotators username
        """
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id, access_level=1)
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_guests(project_id: int) -> List[str]:
        """Get guests of a project

        Args:
            project_id (int)

        Returns:
            List[str]: list of guests username
        """
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id, access_level=4)
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_all(project_id: int):
        """Get all accesses of project

        Args:
            project_id (int)

        Returns:
            list of usernames of every type of user access
        """
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id).all()
        admins, validators, annotators, guests = [], [], [], []
        for project_access in project_access_list: 
            username = UserService.get_by_id(project_access.user_id).username
            if project_access.access_level == 4: guests.append(username)
            elif project_access.access_level == 1: annotators.append(username)
            elif project_access.access_level == 2: validators.append(username)
            elif project_access.access_level == 3: admins.append(username)
        return admins, validators, annotators, guests

    @staticmethod
    def get_users_role(project_id: int) -> Dict[str, List[str]]:
        admins = ProjectAccessService.get_admins(project_id)
        validators = ProjectAccessService.get_validators(project_id)
        annotators = ProjectAccessService.get_annotators(project_id)
        guests = ProjectAccessService.get_guests(project_id)
        return {
            "admins": admins,
            "validators": validators,
            "annotators": annotators,
            "guests": guests,
        }


    @staticmethod
    def require_access_level(project_id, required_access_level) -> None:
        access_level = 0
        if current_user.is_authenticated:
            if current_user.super_admin:
                return 
            else:
                access_level = ProjectAccessService.get_by_user_id(
                    current_user.id, project_id
                ).access_level

        if access_level >= required_access_level:
            return
        else:
            abort(403)

    
    @staticmethod
    def require_access_level(project_id, required_access_level) -> None:
        access_level = 0
        if current_user.is_authenticated:
            if current_user.super_admin:
                return 
            else:
                access_level = ProjectAccessService.get_by_user_id(
                    current_user.id, project_id
                ).access_level

        if access_level >= required_access_level:
            return
        else:
            abort(403)

    @staticmethod
    def check_admin_access(project_id) -> None:
        """
            Will check, for a project, if user is admin (or super_admin). If not, the service will interupt the controller (abort) and return a 
            401 error with the corresponding error message :
            - User not loged in
            - User doesn't belong to this project
            - User doesn't have admin rights on this projects
        Args:
            project_id (int)
        """


        if not current_user.is_authenticated:
            abort(401, "User not logged in")
        
        # super_admin have access to all projects
        if current_user.super_admin:
            return

        user_id = current_user.id
        project_user_access = ProjectAccessService.get_by_user_id(user_id, project_id)
        if not project_user_access:
            abort(401, "User doesn't belong to this project")

        if project_user_access.access_level != 3:
            abort(401, "User doesn't have admin rights on this projects")

    
    @staticmethod
    def check_project_access(visibility, project_id):
        """
            If the project is private (visibility==0) , it's readable only by its users and by the superadmins
            else the public and the open projects are readable by all the users even those who are not logged in
        Args:
            visibility(int): project visibility
            project_id(int)
        Return:
            boolean
        """
        if visibility == 0:
            if not current_user.is_authenticated:
               return False
            if current_user.super_admin:
                return True
            return ProjectAccessService.get_by_user_id(current_user.id, project_id)   
        else:
            return True
        
    @staticmethod
    def get_cache_key():
        """
            All users have their own cache, and to access to the cache
            you have to use key in our case keys are string concat with user_id
            if user is logged in else it's only string 

        Returns:
            string
        """
        if current_user.is_authenticated: 
            return 'projects_list_user_{}'.format(current_user.id)
        else:
            return 'projects_list_non_logged_in'
            
class ProjectFeatureService:
    """Class that deals with project features to be shown in the tree view"""

    @staticmethod
    def create(new_attrs) -> ProjectFeature:
        """Create new project feature

        Args:
            new_attrs (dict)

        Returns:
            ProjectFeature: new project feature entity
        """
        new_project_access = ProjectFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: str) -> List[str]:
        """Get all features of project based on project id

        Args:
            project_id (str)

        Returns:
            List[str]
        """
        features = ProjectFeature.query.filter_by(project_id=project_id).all()
        if features:
            return [f.value for f in features]
        else:
            return []

    @staticmethod
    def delete_by_project_id(project_id: str) -> str:
        """Delete features by project id

        Args:
            project_id (str)
        """
        features = ProjectFeature.query.filter_by(project_id=project_id).all()
        for feature in features:
            db.session.delete(feature)
            db.session.commit()
        return project_id


class ProjectMetaFeatureService:
    """Class that deals with metaFeatue entity"""
    @staticmethod
    def create(new_attrs) -> ProjectMetaFeature:
        new_project_access = ProjectMetaFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: str) -> List[str]:
        meta_features = ProjectMetaFeature.query.filter_by(project_id=project_id).all()

        if meta_features:
            return [meta_feature.value for meta_feature in meta_features]
        else:
            return []

    @staticmethod
    def delete_by_project_id(project_id: str) -> str:
        features = ProjectMetaFeature.query.filter_by(project_id=project_id).all()
        for feature in features:
            db.session.delete(feature)
            db.session.commit()
        return project_id


class LastAccessService:
    """Class that contains methods that deal with last access entity"""
    
    @staticmethod
    def get_user_by_last_access_and_project(project_name, last_access, access_type):
        """Get username of the user who had the last access of read or write in the project

        Args:
            project_name (str)
            last_access (int)
            access_type (str): write | read

        Returns:
            username(str)
        """
        project_id = ProjectService.get_by_name(project_name).id
        if access_type == 'write':
            user_id = LastAccess.query.filter_by(project_id=project_id, last_write=last_access).first().user_id
        else:
            user_id = LastAccess.query.filter_by(project_id=project_id, last_read=last_access).first().user_id
        username = UserService.get_by_id(user_id).username
        return username        
        
    @staticmethod
    def get_project_last_access(project_name):
        """Get last accesses to the project

        Args:
            project_name (str)

        Returns:
            last_read, last_write(Tuple(int, int))
        """
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)
        last_accesses: LastAccess = LastAccess.query.filter(LastAccess.project_id == project.id)
        last_read = max(
            (last_access.last_read for last_access in last_accesses if last_access.last_read is not None)
            , default=0
        )
        last_write = max(
            (last_access.last_write for last_access in last_accesses if last_access.last_write is not None)
            , default= 0
        )
        return last_read, last_write
    
    @staticmethod
    def update_last_access_per_user_and_project(user_id, project_name, access_type):
        """Update or cerate the last access entity of the user for specific project

        Args:
            user_id (str): the last user who visited or write in the project
            project_name (str)
            access_type (str): write | read
        """
        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)

        last_access: LastAccess = LastAccess.query.filter(LastAccess.user_id == user_id).filter(LastAccess.project_id == project.id).first()
        
        time_now_ts = datetime.datetime.now().timestamp()

        if not last_access:
            new_data = {
                "project_id": project.id,
                "user_id": user_id,
                "last_write": None if (access_type == "read") else time_now_ts,
                "last_read": time_now_ts,
            }
            new_last_access = LastAccess(**new_data)
            db.session.add(new_last_access)
            db.session.commit()

        else:
            if access_type == "read":
                last_access.last_read = time_now_ts
            else:
                last_access.last_write = time_now_ts
                last_access.last_read = time_now_ts
            db.session.commit()
