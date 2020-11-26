from app.utils.grew_utils import GrewService

project_name_test = "tdd_1"
sample_name_test = "1a.prof.trees.all"


def test_get_sample_trees():
    sample_trees = GrewService.get_sample_trees(project_name_test, sample_name_test)
    assert sample_trees['1604672339.027225-49649_00001']