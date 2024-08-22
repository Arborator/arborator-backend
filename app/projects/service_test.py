from typing import List
from datetime import datetime

from flask_sqlachemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

from .model import Project, ProjectAccess, ProjectFeature, ProjectMetaFeature, LastAccess 
from .service import ProjectService, ProjectAccessService, ProjectFeatureService, ProjectMetaFeatureService, LastAccessService
from .interface import ProjectInterface

class TestProjectService:
    
    def test_get_all(self, db:SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        second_project: Project = Project(
            id=2,
            project_name="second_project",
            description="Project for test",
            image="/path/to/image2",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="ud",
            language="French"
        )
        db.session.add(first_project)
        db.session.add(second_project)
        db.session.commit()
        
        results = List[Project] = ProjectService.get_all()
        assert len(results) == 2
        assert first_project in results and second_project in results
            
    def test_create(self):
        first_project: ProjectInterface = {
            "id": 2,
            "project_name": "second_project",
            "description": "Project for test",
            "image": "/path/to/image2",
            "visibility": 0,
            "blind_annotation_mode": False,
            "freezed": False,
            "config": "ud",
            "language":"French"
        }
        ProjectService.create(first_project)
        results = List[Project] = ProjectService.get_all()
        assert len(results) == 1
        for k in first_project.keys():
            assert getattr(results[0], k) == first_project[k]

    def test_get_by_name(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        second_project: Project = Project(
            id=2,
            project_name="second_project",
            description="Project for test",
            image="/path/to/image2",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="ud",
            language="French"
        )
        db.session.add(first_project)
        db.session.add(second_project)
        db.session.commit()
        
        first_retrieved_project = ProjectService.get_by_name("first_project")
        second_retrieved_project= ProjectService.get_by_name("second_project")
        
        assert first_retrieved_project.project_name == 'first_project'
        assert first_retrieved_project.id == 1
        
        assert second_retrieved_project.project_name == 'second_project'
        assert second_retrieved_project.id == 2
    
    def test_update(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        db.session.add(first_project)
        db.session.commit()
        
        updates: ProjectInterface = {
            "description": "This is a new description",
            "blind_annotation_mode": True,
        }
        
        ProjectService.update(first_project, updates)
        
        result: Project = Project.query.get(first_project.id).first()
        assert result.description == 'This is a new description'
        assert result.blind_annotation_mode == True
        
    def test_delete_by_name(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        second_project: Project = Project(
            id=2,
            project_name="second_project",
            description="Project for test",
            image="/path/to/image2",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="ud",
            language="French"
        )
        
        db.session.add(first_project)
        db.session.add(second_project)
        db.session.commit()
        
        ProjectService.delete_by_name("first_project")
        
        results: List[Project] = ProjectService.get_all()
        
        assert len(results) == 1
        assert first_project not in results and second_project in results
        
    def test_check_if_project_exist(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        second_project: Project = Project(
            id=2,
            project_name="second_project",
            description="Project for test",
            image="/path/to/image2",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="ud",
            language="French"
        )
        
        db.session.add(first_project)
        db.session.add(second_project)
        db.session.commit()
        
        ProjectService.delete_by_name("first_project")
        project_1 = ProjectService.get_by_name("first_project")
        
        with pytest.raises(HTTPException) as http_error:
            ProjectService.check_if_project_exist(project_1)
        
        assert http_error.value.code == 404
        assert http_error.value.detail == 'There was no such project stored on arborator backend'
        
    def test_check_if_freezed(self, db: SQLAlchemy):
        
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=True,
            config="sud",
            language="English"
        )
        db.session.add(first_project)
        db.session.commit()
        
        ProjectAccessService.create(
            {
                "user_id": "arbo.test@gmail.com",
                "project_id": 1,
                "access_level": 3,
            }
        )
        project = ProjectService.get_by_name("first_project")
        with pytest.raises(HTTPException) as http_error:
            ProjectService.check_if_freezed(project)
        assert http_error.value.code == 403
        assert http_error.value.detail == "You can't access the project when it's freezed"

class TestProjectAccessService:
    
    def test_create(self):
        first_access = dict(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        ProjectAccessService.create(first_access)
        
        results: List[ProjectService] = ProjectAccessService.query.all()
        assert len(results) == 1
        for k in first_access.keys():
            assert getattr(results[0], k) == first_access[k]
    
    def test_update(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test2@gmail.com",
            access_level=2
        )
        db.session.add(first_access)
        db.session.commit()
        
        updates = { "access_level": 3 }
        ProjectAccessService.update(updates)
        result: ProjectAccess = ProjectAccess.query.get(first_access.id).first()
        assert result.access_level == 3
        
    def test_delete(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        second_access: ProjectAccess = ProjectAccess(
            id=2,
            project_id=2,
            user_id="arbo.test2@gmail.com"
        )
        db.session.add(first_access)
        db.session.add(second_access)
        db.session.commit()
        
        ProjectAccessService.delete('arbo.test@gmail.com', 1)
        results: List[ProjectAccess] = ProjectAccess.query().all()
        
        assert len(results) == 1
        assert first_access not in results and second_access in results
        
    def test_get_by_user_id(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        db.session.add(first_access)
        db.session.commit()
        
        result = ProjectAccessService.get_by_user_id("arbo.test@gmail.com", 1)
        assert result.access_level == 3
        
    def test_get_admins(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        second_access: ProjectAccess = ProjectAccess(
            id=2,
            project_id=1,
            user_id="arbo.test2@gmail.com",
            access_level=2
        )
            
        
        db.session.add(first_access)
        db.session.add(second_access)
        db.session.commit()
        
        results = ProjectAccessService.get_admins(1)
        
        assert len(results) == 1
        assert results[0].user_id == "arbo.test@gmail.com"
        
    def test_get_validators(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        second_access: ProjectAccess = ProjectAccess(
            id=2,
            project_id=1,
            user_id="arbo.test2@gmail.com",
            access_level=2
        )
            
        
        db.session.add(first_access)
        db.session.add(second_access)
        db.session.commit()
        
        results = ProjectAccessService.get_validators(1)
        
        assert len(results) == 1
        assert results[0].user_id == "arbo.test2@gmail.com"
    
    def test_get_annotators(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        second_access: ProjectAccess = ProjectAccess(
            id=2,
            project_id=1,
            user_id="arbo.test3@gmail.com",
            access_level=1
        )
            
        
        db.session.add(first_access)
        db.session.add(second_access)
        db.session.commit()
        
        results = ProjectAccessService.get_annotators(1)
        
        assert len(results) == 1
        assert results[0].user_id == "arbo.test3@gmail.com" 
    
    def test_get_guests(self, db: SQLAlchemy):
        first_access: ProjectAccess = ProjectAccess(
            id=1,
            project_id=1,
            user_id="arbo.test@gmail.com",
            access_level=3
        )
        second_access: ProjectAccess = ProjectAccess(
            id=2,
            project_id=1,
            user_id="arbo.test4@gmail.com",
            access_level=4
        )
            
        
        db.session.add(first_access)
        db.session.add(second_access)
        db.session.commit()
        
        results = ProjectAccessService.get_annotators(1)
        
        assert len(results) == 1
        assert results[0].user_id == "arbo.test4@gmail.com" 
        
    
class TestProjectFeatureService:
    
    def test_create(self):
        first_feature = {
          "id": 1,
          "project_id": 1, 
          "value": "FORM" 
        }
        ProjectFeatureService.create(first_feature)
        results: List[ProjectFeature] = ProjectFeature.query.all()
        
        assert len(results) == 1
        assert results[0].value == "FORM"
        
    def test_get_by_project_id(self, db):
        first_feature: ProjectFeature = ProjectFeature(
            id = 1,
            project_id = 1,
            value = "FORM",    
        )
        second_feature: ProjectFeature = ProjectFeature(
            id = 2,
            project_id = 1,
            value = "UPOS"
        )
        db.session.add(first_feature)
        db.session.add(second_feature)
        db.session.commit()
        
        results = ProjectFeatureService.get_by_project_id(1)
        assert len(results) == 2
        assert first_feature.value in results and second_feature.value in results
        
    def test_delete_by_project_id(self, db:SQLAlchemy):
        first_feature: ProjectFeature = ProjectFeature(
            id = 1,
            project_id = 1,
            value = "FORM",    
        )
        second_feature: ProjectFeature = ProjectFeature(
            id = 2,
            project_id = 1,
            value = "UPOS"
        )
        db.session.add(first_feature)
        db.session.add(second_feature)
        db.session.commit()
        
        ProjectFeatureService.delete_by_project_id(1)
        results = ProjectFeature.query.all()
        assert results == None
        
class TestProjectMetaFeature:
    def test_create(self):
        first_meta_feature = {
          "id": 1,
          "project_id": 1, 
          "value": "text_en" 
        }
        ProjectMetaFeatureService.create(first_meta_feature)
        results: List[ProjectMetaFeature] = ProjectMetaFeature.query.all()
        
        assert len(results) == 1
        assert results[0].value == "text_en"
        
    def test_get_by_project_id(self, db):
        first_meta_feature: ProjectMetaFeature = ProjectMetaFeature(
            id = 1,
            project_id = 1,
            value = "text_en",    
        )
        second_meta_feature: ProjectMetaFeature = ProjectMetaFeature(
            id = 2,
            project_id = 1,
            value = "phonetic_text"
        )
        db.session.add(first_meta_feature)
        db.session.add(second_meta_feature)
        db.session.commit()
        
        results = ProjectMetaFeatureService.get_by_project_id(1)
        assert len(results) == 2
        assert first_meta_feature.value in results and second_meta_feature.value in results
        
    def test_delete_by_project_id(self, db:SQLAlchemy):
        first_meta_feature: ProjectMetaFeature = ProjectMetaFeature(
            id = 1,
            project_id = 1,
            value = "FORM",    
        )
        second_meta_feature: ProjectMetaFeature = ProjectMetaFeature(
            id = 2,
            project_id = 1,
            value = "UPOS"
        )
        db.session.add(first_meta_feature)
        db.session.add(second_meta_feature)
        db.session.commit()
        
        ProjectMetaFeatureService.delete_by_project_id(1)
        results = ProjectMetaFeature.query.all()
        assert results == None
        

class TestLastAccessService:
    
    @pytest.mark.parametrize(
        "last_accesses", "expected_last_read", "expected_last_write"
        [
            ([1713857865.12323, None, 1713452667.56323, 1713452391.73287], 1713857865.12323, 1713452391.73287),
            ([1713857865.12323, 1713857865.12323, 1713952667.56323, 1713452391.73287], 1713952667.56323, 1713857865.12323),
        ]
    )
    def test_get_project_last_access(self,last_accesses, expected_last_write, expected_last_read, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        first_last_access: LastAccess = LastAccess(
            id=1,
            user_id="arbo.test@gmail.com",
            project_id=1,
            last_read=last_accesses[0],
            last_write=last_accesses[1]
        )
        second_last_access: LastAccess = LastAccess(
            id=1,
            user_id="arbo.test2@gmail.com",
            project_id=1,
            last_read=last_accesses[2],
            last_write=last_accesses[3]
        )
        db.session.add(first_project)
        db.session.add(first_last_access)
        db.session.add(second_last_access)
        db.session.commit()
        
        last_read, last_write = LastAccessService.get_project_last_access(1)
        assert expected_last_write == last_write and expected_last_read == last_read
    
    def test_create_new_last_access_per_user_and_project(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        db.session.add(first_project)
        db.session.commit()
        
        LastAccessService.update_last_access_per_user_and_project("arbo.test2@gmail.com", "first_project", "write")
        last_access: List[LastAccess] = LastAccess.query.all()
        
        assert len(last_access) == 1
        
    def test_update_last_access_per_user_and_project(self, db: SQLAlchemy):
        first_project: Project = Project(
            id=1,
            project_name="first_project",
            description="",
            image="/path/to/image",
            visibility=0,
            blind_annotation_mode=False,
            freezed=False,
            config="sud",
            language="English"
        )
        time_now_ts = datetime.now().timestamp()
        first_last_access: LastAccess = LastAccess(
            id=1,
            user_id="arbo.test@gmail.com",
            project_id=1,
            last_read=time_now_ts,
            last_write=time_now_ts,
        )
        db.session.add(first_project)
        db.session.add(first_last_access)
        db.session.commit()
        
        LastAccessService.update_last_access_per_user_and_project("arbo.test@gmail.com","first_project",'read')
        LastAccessService.update_last_access_per_user_and_project("arbo.test@gmail.com","first_project",'write')

        last_read, last_write = LastAccessService.get_project_last_access("first_project")
        assert last_read != time_now_ts and last_write != time_now_ts

        
