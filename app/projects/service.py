from datetime import datetime
from typing import Dict, List, Tuple

from flask import abort, current_app
from flask_login import current_user

from app import db
from app.utils.grew_utils import grew_request
from ..user.model import User
from .interface import ProjectInterface
from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature, LastAccess
from ..user.service import UserService


class ProjectService:
    @staticmethod
    def get_all() -> List[Project]:
        return Project.query.all()

    @staticmethod
    def create(new_attrs: ProjectInterface) -> Project:
        new_project = Project(**new_attrs)
        db.session.add(new_project)
        db.session.commit()
        return new_project

    @staticmethod
    def get_by_name(project_name: str) -> Project:
        return Project.query.filter(Project.project_name == project_name).first()

    @staticmethod
    def update(project: Project, changes) -> Project:
        project.update(changes)
        db.session.commit()
        return project

    @staticmethod
    def delete_by_name(project_name: str) -> str:
        project = Project.query.filter(
            Project.project_name == project_name).first()
        if not project:
            return ""
        db.session.delete(project)
        db.session.commit()
        return project_name
    
    @staticmethod
    def rename_project(project_name: str, new_project_name): 
        reply = grew_request("renameProject", data= {
            "project_id": project_name,
            "new_project_id": new_project_name
        })
        if reply["status"] != 'OK':
            abort(404)
        
    @staticmethod
    def change_image(project_name, value):
        """ set a project image (path) and return the new project  """
        project = Project.query.filter(
            Project.project_name == project_name).first()
        project.image = value
        db.session.commit()
        print('change_image done')
        return project

    @staticmethod
    def check_if_project_exist(project: Project) -> None:
        if not project:
            message = "There was no such project stored on arborator backend"
            abort(404, {"message": message})
    
    @staticmethod 
    def check_if_freezed(project: Project) -> None:
        if project.freezed and ProjectAccessService.get_admins(project.id)[0] != current_user.username: 
            abort(403, "You can't access the project when it's freezed")

   
class ProjectAccessService:
    @staticmethod
    def create(new_attrs) -> ProjectAccess:
        new_project_access = ProjectAccess(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def update(project_access: ProjectAccess, changes):
        project_access.update(changes)
        db.session.commit()
        return project_access

    @staticmethod
    def delete(user_id: str, project_id: int):
        project_access_list = ProjectAccess.query.filter_by(
            user_id=user_id, project_id=project_id
        ).all()
        if not project_access_list:
            return []
        for project_access in project_access_list:
            db.session.delete(project_access)
            db.session.commit()
        return [(project_id, user_id)]

    # TODO : Rename this as `get_by_username` because we are not fetching the user_id
    # ... but the username
    @staticmethod
    def get_by_user_id(user_id: str, project_id: str) -> ProjectAccess:
        return ProjectAccess.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()

    @staticmethod
    def get_admins(project_id: str) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=3
        )
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_validators(project_id: str) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=2
        )
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []
        
    @staticmethod
    def get_annotators(project_id: str) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=1
        )
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_guests(project_id: str) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=4
        )
        if project_access_list:
            return [UserService.get_by_id(project_access.user_id).username for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_all(project_id: int) -> Tuple[List[str], List[str]]:
        '''optimized version dedicated to homepage. reduces the database calls but makes the code less pretty'''
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(project_id=project_id).all()
        admins, validators, annotators, guests = [], [], [], []
        for project_access in project_access_list: 
            username = UserService.get_by_id(project_access.user_id).username
            if project_access.access_level==4: guests.append(username)
            elif project_access.access_level==1: annotators.append(username)
            elif project_access.access_level==2: validators.append(username)
            elif project_access.access_level==3: admins.append(username)
        return admins, validators, annotators, guests

    @staticmethod
    def get_users_role(project_id: str) -> Dict[str, List[str]]:
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
                pass

            else:
                access_level = ProjectAccessService.get_by_user_id(
                    current_user.id, project_id
                ).access_level.code

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

        if project_user_access.access_level.value != "admin":
            abort(401, "User doesn't have admin rights on this projects")

        return
    
    @staticmethod
    def check_project_access(visibility,project_id):
        """
        If the project is private (visibility==0) , it's readable only by its users and by the superadmins
        else the public and the open projects are readable by all the users even those who are not logged in
        """
        if visibility == 0:
            if not current_user.is_authenticated:
               return False
            if current_user.super_admin:
                return True
            return ProjectAccessService.get_by_user_id(current_user.id, project_id)   
        else:
            return True
            
class ProjectFeatureService:
    @staticmethod
    def create(new_attrs) -> ProjectFeature:
        new_project_access = ProjectFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: str) -> List[str]:
        features = ProjectFeature.query.filter_by(project_id=project_id).all()
        if features:
            return [f.value for f in features]
        else:
            return []

    @staticmethod
    def delete_by_project_id(project_id: str) -> str:
        """TODO : Delete all the project features at once. This is a weird way of doing, but it's because we have a table specificaly
        ...dedicated for linking project shown features and project. Maybe a simple textfield in the project settings would do the job"""
        features = ProjectFeature.query.filter_by(project_id=project_id).all()
        for feature in features:
            db.session.delete(feature)
            db.session.commit()
        return project_id


class ProjectMetaFeatureService:
    @staticmethod
    def create(new_attrs) -> ProjectMetaFeature:
        new_project_access = ProjectMetaFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: str) -> List[str]:
        meta_features = ProjectMetaFeature.query.filter_by(
            project_id=project_id).all()

        if meta_features:
            return [meta_feature.value for meta_feature in meta_features]
        else:
            return []

    @staticmethod
    def delete_by_project_id(project_id: str) -> str:
        """Delete all the project features at once. This is a weird way of doing, but it's because we have a table specificaly
        ...dedicated for linking project shown features and project. Maybe a simple textfield in the project settings would do the job"""
        features = ProjectMetaFeature.query.filter_by(
            project_id=project_id).all()
        for feature in features:
            db.session.delete(feature)
            db.session.commit()
        return project_id


class LastAccessService:

    @staticmethod
    def get_project_last_access(project_name):
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
        if access_type not in ["read", "write"]:
            raise f"ERROR by the coder in LastAccessService, access_type not in 'read' 'write'"

        project = ProjectService.get_by_name(project_name)
        ProjectService.check_if_project_exist(project)

        last_accesss: LastAccess = LastAccess.query.filter(LastAccess.user_id == user_id).filter(LastAccess.project_id == project.id).first()
        
        time_now_ts = datetime.now().timestamp()

        if not last_accesss:
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
                last_accesss.last_read = time_now_ts
            else:
                last_accesss.last_write = time_now_ts
            db.session.commit()
