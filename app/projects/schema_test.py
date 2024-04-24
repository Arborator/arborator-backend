from pytest import fixture

from .schema import ProjectSchema
from .interface import ProjectInterface
from .model import Project

@fixture
def project_schema() -> ProjectSchema:
    return ProjectSchema()

def test_project_schema_create(project_schema: ProjectSchema):
    assert project_schema
    
def test_project_schema_works(project_schema: ProjectSchema):
    params: ProjectInterface = project_schema.load(
        {
            'id': '1',
            'projectName': 'arbo_test',
            'description': 'Project for test',
            'image': 'path/to/image',
            'visibility': '0',
            'blindAnnotationMode': 'False',
            'freezed': 'False',
            'config': 'sud',
            'language': 'English',
        }
    )
    project = Project(**params)
    assert project.id == '1'
    assert project.project_name == 'arbo_test'
    assert project.description == 'Project for test'
    assert project.image == 'path/to/image'
    assert project.blind_annotation_mode == 'False'
    assert project.freezed == 'False'
    assert project.config == 'sud'
    assert project.language == "English"
    

    

