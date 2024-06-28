from pytest import fixture
from flask_sqlalchemy import SQLAlchemy

from .model import Project, ProjectFeature, ProjectMetaFeature, ProjectAccess, LastAccess

@fixture
def project() -> Project: 
    return Project(
        id=1,
        project_name="test_project",
        description="Project for test",
        image="/path/to/image",
        visibility=0,
        blind_annotation_mode=False,
        diff_mode=False,
        diff_user_id=None,
        freezed=False,
        config="sud",
        language="English"
    )

def test_project_create(project: Project):
    assert project

def test_project_retreive(project: Project, db: SQLAlchemy ):
    db.session.add(project)
    db.session.commit()
    project_test = Project.query.first()
    assert project_test.__dict__ == project.__dict__

def project_feature() -> ProjectFeature:
    return ProjectFeature(
        id=1,
        value="FORM", 
        project_id=1
    )

def test_project_feature_create(project_feature: ProjectFeature):
    assert project_feature

def test_project_feature_retreive(project_feature: ProjectFeature, db: SQLAlchemy):
    db.session.add(project_feature)
    db.session.commit()
    project_feature_test = ProjectFeature.query.first()
    assert project_feature_test.__dict__ == project_feature.__dict__


def project_meta_feature() -> ProjectMetaFeature:
    return ProjectMetaFeature(
        id=1,
        value="text_en",
        project_id=1
    )

def test_project_meta_feature_create(project_meta_feature: ProjectMetaFeature):
    assert project_meta_feature
    
def test_project_meta_feature_retreive(project_meta_feature: ProjectMetaFeature, db: SQLAlchemy):
    db.session.add(project_meta_feature)
    db.session.commit()
    project_meta_feature_test = ProjectMetaFeature.query.first()
    assert project_meta_feature_test.__dict__ == project_meta_feature.__dict__
    

def project_access() -> ProjectAccess:
    return ProjectAccess(
        id=1,
        project_id=1,
        user_id="5788",
        access_level=3
    )

def test_project_access_create(project_access: ProjectAccess):
    assert project_access

def test_project_access_retreive(project_access: ProjectAccess, db: SQLAlchemy):
    db.session.add(project_access)
    db.session.commit()
    project_access_test = ProjectAccess.query.first()
    assert project_access_test.__dict__ == project_access.__dict__

def last_access() -> LastAccess:
    return LastAccess(
        id=1,
        user_id="5788",
        project_id=1,
        last_read=1713528567.2663,
        last_write=1713526493.33404
    )
    
def test_last_access_create(last_access: LastAccess):
    assert last_access
    
def test_last_access_retreive(last_access: LastAccess, db: SQLAlchemy):
    db.session.add(last_access)
    db.session.commit()
    last_access_test = LastAccess.query.first()
    assert last_access_test.__dict__ == last_access.__dict__
    