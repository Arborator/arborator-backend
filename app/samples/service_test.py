from app.samples.service import SampleEvaluationService
from app.utils.grew_utils import GrewService

project_name_test = "tdd_1"
sample_name_test = "1a.prof.trees.all"

def test_evaluate_sample_trees():
    sample_trees = GrewService.get_sample_trees(project_name_test, sample_name_test)
    evaluations = SampleEvaluationService.evaluate_sample(sample_trees)
    assert evaluations

def test_evaluations_json_to_tsv():
    sample_trees = GrewService.get_sample_trees(project_name_test, sample_name_test)
    evaluations = SampleEvaluationService.evaluate_sample(sample_trees)

    evaluations_tsv = SampleEvaluationService.evaluations_json_to_tsv(evaluations)
    assert evaluations_tsv