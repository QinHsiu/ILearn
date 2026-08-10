from pathlib import Path

import pytest

from ilearn.core.grading import StepGrader
from ilearn.eval.runner import (
    EvalMetrics,
    final_correct_accuracy,
    json_valid_rate,
    load_fixtures,
    macro_f1_error_tags,
    run_eval,
    tag_set_f1,
)

_FIXTURES_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "eval" / "step_grading_fixtures.json"
)


def test_final_correct_accuracy_toy():
    expected = [True, False, True, False]
    predicted = [True, True, True, False]
    assert final_correct_accuracy(expected, predicted) == 0.75


def test_final_correct_accuracy_empty():
    assert final_correct_accuracy([], []) == 0.0


def test_tag_set_f1_both_empty():
    assert tag_set_f1(set(), set()) == 1.0


def test_tag_set_f1_one_empty():
    assert tag_set_f1({"misread"}, set()) == 0.0
    assert tag_set_f1(set(), {"misread"}) == 0.0


def test_tag_set_f1_perfect_overlap():
    assert tag_set_f1({"misread", "calc_error"}, {"calc_error", "misread"}) == 1.0


def test_tag_set_f1_partial_overlap():
    assert tag_set_f1({"misread"}, {"misread", "calc_error"}) == pytest.approx(2 / 3)


def test_macro_f1_error_tags_toy():
    expected = [["misread"], ["calc_error"], []]
    predicted = [["misread"], ["concept_gap"], []]
    assert macro_f1_error_tags(expected, predicted) == pytest.approx(1 / 3)


def test_json_valid_rate_toy():
    assert json_valid_rate([True, True, False]) == pytest.approx(2 / 3)
    assert json_valid_rate([]) == 0.0


def test_load_fixtures_count_and_shape():
    fixtures = load_fixtures(_FIXTURES_PATH)
    assert len(fixtures) >= 12
    first = fixtures[0]
    assert first.id
    assert first.item
    assert isinstance(first.student_answer, str)
    assert isinstance(first.expected_final_correct, bool)
    assert isinstance(first.expected_error_tags, list)
    assert any(
        fixture.item.get("type") == "constructed"
        and fixture.item.get("answer_key")
        and len(fixture.student_answer.split()) > 3
        for fixture in fixtures
    )


def test_run_eval_offline_matches_fixtures():
    metrics = run_eval(_FIXTURES_PATH, grader=StepGrader(None))
    assert isinstance(metrics, EvalMetrics)
    assert 0.8 <= metrics.accuracy <= 1.0
    assert 0.8 <= metrics.macro_f1 <= 1.0
    assert metrics.json_valid_rate == 1.0


def test_run_eval_empty_fixtures(tmp_path: Path):
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    metrics = run_eval(empty)
    assert metrics == EvalMetrics(accuracy=0.0, macro_f1=0.0, json_valid_rate=0.0)
