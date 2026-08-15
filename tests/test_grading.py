from unittest.mock import MagicMock, patch

import pytest

from ilearn.core.grading import StepGrader, answers_match, match_answer_detailed, normalize_answer
from ilearn.core.schemas import AssessmentItem, AssessmentPaper, StudentAnswer, StudentProfile
from ilearn.providers.llm import LLMClient


def make_choice(answer_key: str = "B", **kwargs) -> AssessmentItem:
    defaults = {
        "id": "item_1",
        "stem": "Pick one",
        "type": "choice",
        "difficulty": "easy",
        "knowledge_ids": ["k1"],
        "answer_key": answer_key,
        "choices": ["A", "B", "C", "D"],
    }
    defaults.update(kwargs)
    return AssessmentItem(**defaults)


def make_fill(answer_key: str = "42", **kwargs) -> AssessmentItem:
    defaults = {
        "id": "fill_1",
        "stem": "Fill in",
        "type": "fill",
        "difficulty": "easy",
        "knowledge_ids": ["k1"],
        "answer_key": answer_key,
    }
    defaults.update(kwargs)
    return AssessmentItem(**defaults)


def make_constructed(**kwargs) -> AssessmentItem:
    defaults = {
        "id": "con_1",
        "stem": "Explain your work",
        "type": "constructed",
        "difficulty": "medium",
        "knowledge_ids": ["k1"],
        "rubric_steps": ["Set up equation", "Solve", "Check answer"],
    }
    defaults.update(kwargs)
    return AssessmentItem(**defaults)


def test_choice_correct_no_llm():
    item = make_choice(answer_key="B")
    g = StepGrader(llm=None).grade_item(item, "B")
    assert g.final_correct is True
    assert g.grading_degraded is False


def test_choice_wrong_tags_without_llm_still_structured():
    g = StepGrader(llm=None).grade_item(make_choice(answer_key="B"), "A")
    assert g.final_correct is False
    assert "concept_gap" in g.error_tags or "misread" in g.error_tags


def test_choice_normalizes_whitespace_and_case():
    item = make_choice(answer_key="b")
    g = StepGrader(llm=None).grade_item(item, "  B  ")
    assert g.final_correct is True


def test_fill_numeric_tolerance():
    item = make_fill(answer_key="3.14")
    g = StepGrader(llm=None).grade_item(item, "3.140000")
    assert g.final_correct is True


def test_fill_wrong_has_error_tags_without_llm():
    g = StepGrader(llm=None).grade_item(make_fill(answer_key="10"), "9")
    assert g.final_correct is False
    assert g.error_tags


def test_constructed_no_llm_degraded():
    g = StepGrader(llm=None).grade_item(make_constructed(), "x = 5")
    assert g.grading_degraded is True
    assert len(g.step_results) >= 1


def test_constructed_offline_uses_final_token_as_answer():
    item = make_constructed(answer_key="60")
    g = StepGrader(llm=None).grade_item(
        item,
        "先算 15 × 4，把 15 加四次，最后答案：60",
    )
    assert g.final_correct is True
    assert g.grading_degraded is True


def test_constructed_offline_rejects_wrong_final_token():
    item = make_constructed(answer_key="60")
    g = StepGrader(llm=None).grade_item(
        item,
        "先算 15 × 4，我误算得到最后答案：55",
    )
    assert g.final_correct is False
    assert g.grading_degraded is True


def test_normalize_answer_strips_and_casefolds():
    assert normalize_answer("  Hello  World ") == "hello world"


def test_answers_match_numeric():
    assert answers_match("3.0", "3")
    assert not answers_match("3.1", "3")


def test_answers_match_fraction_equivalence():
    assert answers_match("2/4", "1/2")
    assert answers_match("½", "0.5")


def test_match_answer_detailed_exposes_math_verify_payload():
    ok, payload = match_answer_detailed("2/4", "1/2")
    assert ok is True
    assert payload is not None
    assert payload["equivalent"] is True
    assert payload["confidence"] > 0.9


def test_answers_match_rejects_unrelated_text():
    assert not answers_match("香蕉", "1/2")


def test_grade_paper():
    paper = AssessmentPaper(
        items=[make_choice(id="c1", answer_key="A"), make_fill(id="f1", answer_key="5")],
        grade=5,
        curriculum_label="test",
    )
    answers = [
        StudentAnswer(item_id="c1", answer_text="A"),
        StudentAnswer(item_id="f1", answer_text="5"),
    ]
    grades = StepGrader(llm=None).grade_paper(paper, answers)
    assert len(grades) == 2
    assert all(g.final_correct for g in grades)


@patch.object(LLMClient, "chat_json")
def test_constructed_with_llm(mock_chat_json):
    mock_chat_json.return_value = {
        "final_correct": True,
        "steps": ["x = 5"],
        "step_results": [
            {
                "step_index": 0,
                "step_text": "Set up equation",
                "status": "correct",
                "comment": "ok",
            }
        ],
        "error_tags": [],
        "knowledge_ids": ["k1"],
        "hint_level_suggestion": "none",
    }
    llm = LLMClient(api_key="sk-test")
    g = StepGrader(llm=llm).grade_item(make_constructed(), "x = 5")
    assert g.final_correct is True
    assert g.grading_degraded is False
    mock_chat_json.assert_called_once()


@patch.object(LLMClient, "chat_json")
def test_llm_filters_invalid_error_tags(mock_chat_json):
    mock_chat_json.return_value = {
        "final_correct": False,
        "steps": ["A"],
        "step_results": [],
        "error_tags": ["concept_gap", "bogus_tag", "misread"],
        "knowledge_ids": ["k1"],
    }
    llm = LLMClient(api_key="sk-test")
    g = StepGrader(llm=llm).grade_item(make_choice(answer_key="B"), "A")
    assert set(g.error_tags).issubset({"concept_gap", "calc_error", "misread", "method_wrong", "incomplete"})
    assert "bogus_tag" not in g.error_tags


@patch.object(LLMClient, "chat_json")
def test_llm_failure_degrades_constructed(mock_chat_json):
    from ilearn.providers.llm import LLMError

    mock_chat_json.side_effect = LLMError("failed")
    llm = LLMClient(api_key="sk-test")
    g = StepGrader(llm=llm).grade_item(make_constructed(), "partial work")
    assert g.grading_degraded is True
