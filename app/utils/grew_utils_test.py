from app.utils.grew_utils import GrewService, get_timestamp

project_name_test = "tdd_1"
sample_name_test = "1a.prof.trees.all"


def test_get_sample_trees():
    sample_trees = GrewService.get_sample_trees(project_name_test, sample_name_test)
    assert sample_trees['1604672339.027225-49649_00001']


has_timestamp = """
# timestamp = 1684250080942.398
# other_meta = useless
"""

has_no_timestamp = """
# not_a_timestamp = 123242.334
# also_not_a timestamp = 2324.2424
"""

def test_true():
    assert get_timestamp(has_timestamp) == "1684250080942.398"
    assert get_timestamp(has_no_timestamp) == False