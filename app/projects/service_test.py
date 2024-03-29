from typing import Dict, List
import json
import base64

from app import db
from flask import abort, current_app
from flask_login import current_user

from .interface import ProjectExtendedInterface, ProjectInterface
from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature, DefaultUserTrees
from ..utils.grew_utils import grew_request


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
