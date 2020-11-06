from typing import Dict, List
import json
import base64

from app import db
from flask import abort, current_app
from flask_login import current_user

from .interface import ProjectExtendedInterface, ProjectInterface
from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature, DefaultUserTrees
from ..utils.grew_utils import grew_request
from ..samples.model import SampleRole


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
    def change_image(project_name, value):
        """ set a project image (blob base64) and return the new project  """
        project = Project.query.filter(
            Project.project_name == project_name).first()
        project.image = value
        db.session.commit()
        return project
    # @staticmethod
    # def get_settings_infos(project_name, current_user):
    #     """ get project informations without any samples """
    #     project = Project.query.filter(Project.project_name == project_name).first()
    #     if not current_user.is_authenticated:  # TODO : handle anonymous user
    #         roles = []
    #     else:
    #         roles = set(SampleRole.query.filter_by(project_id = project.id, user_id = current_user.id).all())
    #     # if not roles and project.is_private: return 403 # removed for now -> the check is done in view and for each actions
    #     admins = [a.user_id for a in ProjectAccess.query.filter_by(project_id=project.id, access_level=2).all()]
    #     guests = [g.user_id for g in ProjectAccess.query.filter_by(project_id=project.id, access_level=1).all()]

    #     # config from arborator
    #     features = ProjectFeature.query.filter_by(project_id=project.id).all()
    #     shown_features =  [f.value for f in features] if features else []

    #     mfs = ProjectMetaFeature.query.filter_by(project_id=project.id)
    #     shown_metafeatures = [mf.value for mf in mfs] if mfs else []

    #     # config from grew
    #     reply = grew_request("getProjectConfig", current_app, data={"project_id": project_name})
    #     if reply["status"] != "OK":
    #         abort(400)
    #     annotationFeatures = reply["data"]
    #     if annotationFeatures is None:
    #         print("This project does not have a configuration stored on grew")

    #     config = {
    #         "shownfeatures": shown_features,
    #         "shownmeta": shown_metafeatures,
    #         "annotationFeatures": annotationFeatures,
    #     }

    #     # cats = [c.value for c in project_dao.find_project_cats(project.id)]
    #     # stocks = project_dao.find_project_stocks(project.id)
    #     # labels = [ {'id':s.id,'labels':[ {"id":l.id, "stock_id":l.stock_id , "value":l.value} for l in project_dao.find_stock_labels(s.id) ]}  for s in stocks ]
    #     defaultUserTrees = [
    #         u.as_json() for u in DefaultUserTrees.query.filter_by(project_id=project.id).all()
    #     ]
    #     # if project.image != None:
    #     #     image = str(base64.b64encode(project.image))
    #     # else:
    #     #     image = ""
    #     settings_info = {
    #         # "name": project.project_name,
    #         # "visibility": project.visibility,
    #         # "description": project.description,
    #         # "image": image,
    #         "config": config,
    #         # "admins": admins,
    #         # "guests": guests,
    #         # "show_all_trees": project.show_all_trees,
    #         # "exercise_mode": project.exercise_mode,
    #         # "default_user_trees": defaultUserTrees,
    #     }
    #     return settings_info


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
            project_id=project_id, access_level=2
        )
        if project_access_list:
            return [project_access.user_id for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_guests(project_id: str) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=1
        )
        if project_access_list:
            return [project_access.user_id for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_users_role(project_id: str) -> Dict[str, List[str]]:
        admins = ProjectAccessService.get_admins(project_id)
        guests = ProjectAccessService.get_guests(project_id)
        return {
            "admins": admins,
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
