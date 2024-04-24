from pytest import fixture

from .interface import ProjectInterface, ProjectExtendedInterface, ProjectShownFeaturesAndMetaInterface
from .model import Project

@fixture
def project_interface() -> ProjectInterface: 
    return ProjectInterface(
        id=1,
        project_name="test_project",
        description="Project for test",
        image="/path/to/image",
        visibility=0,
        blind_annotation_mode=False,
        freezed=False,
        config="sud",
        language="English"
    )

def test_project_interface_create(project_interface: ProjectInterface):
    assert project_interface

def test_project_interface_retreive(project_interface: ProjectInterface):
    project = Project(**project_interface)
    assert project
    
def project_extended_interface() -> ProjectExtendedInterface:
    return ProjectExtendedInterface(
      users=['arbo_admin', 'arbo_user'],
      admins=['arbo_admin'],
      validators=[],
      annotators=['arbo_user'],
      guests=['arbo_guest'],
      number_sentences=54,
      number_samples=4,
      number_trees=78,
      number_tokens=1000,
    )

def project_extended_interface_create(project_extended_interface: ProjectExtendedInterface):
    assert project_extended_interface
    
def project_shown_features_and_meta_interface() -> ProjectShownFeaturesAndMetaInterface:
    return ProjectShownFeaturesAndMetaInterface(
        shown_features=["FORM", "UPOS", "LEMMA", "MISC.Gloss"],
        shown_meta=["text_en", "text"]
    )

def project_shown_features_and_meta_interface_create(project_shown_features_and_meta_interface: ProjectShownFeaturesAndMetaInterface):
    assert project_shown_features_and_meta_interface

