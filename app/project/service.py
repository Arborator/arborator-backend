from app import project
import json
from typing import Dict, List

from app import db
from app.project.schema import ProjectSchema
from app.utils.grew_utils import grew_request
from flask import abort, current_app

from .interface import ProjectExtendedInterface, ProjectInterface
from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature


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
        project = Project.query.filter(Project.project_name == project_name).first()
        if not project:
            return ""
        db.session.delete(project)
        db.session.commit()
        return project_name


class ProjectAccessService:
    @staticmethod
    def create(new_attrs) -> ProjectAccess:
        new_project_access = ProjectAccess(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def update(project_access, changes):
        project_access.update(changes)
        db.session.commit()
        return project_access

    @staticmethod
    def delete(user_id: str, project_id: str):
        project_access_list = ProjectAccess.query.filter_by(
            user_id=user_id, project_id=project_id
        ).all()
        if not project_access_list:
            return []
        for project_access in project_access_list:
            db.session.delete(project_access)
            db.session.commit()
        return [(project_id, user_id)]

    @staticmethod
    def get_by_user_id(user_id: str, project_id: str) -> ProjectAccess:
        return ProjectAccess.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()

    @staticmethod
    def get_admins(project_id: int) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=2
        )
        if project_access_list:
            return [project_access.user_id for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_guests(project_id: int) -> List[str]:
        project_access_list: List[ProjectAccess] = ProjectAccess.query.filter_by(
            project_id=project_id, access_level=1
        )
        if project_access_list:
            return [project_access.user_id for project_access in project_access_list]
        else:
            return []

    @staticmethod
    def get_users_role(project_id: int) -> Dict[str, List[str]]:
        admins = ProjectAccessService.get_admins(project_id)
        guests = ProjectAccessService.get_guests(project_id)
        return {
            "admins": admins,
            "guests": guests,
        }


class ProjectFeatureService:
    @staticmethod
    def create(new_attrs) -> ProjectFeature:
        new_project_access = ProjectFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: int) -> List[str]:
        features = ProjectFeature.query.filter_by(project_id=project_id).all()
        if features:
            return [f.value for f in features]
        else:
            return []


class ProjectMetaFeatureService:
    @staticmethod
    def create(new_attrs) -> ProjectMetaFeature:
        new_project_access = ProjectMetaFeature(**new_attrs)
        db.session.add(new_project_access)
        db.session.commit()
        return new_project_access

    @staticmethod
    def get_by_project_id(project_id: int) -> List[str]:
        meta_features = ProjectMetaFeature.query.filter_by(project_id=project_id).all()

        if meta_features:
            return [meta_feature.value for meta_feature in meta_features]
        else:
            return []
