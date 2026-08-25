"""Tests for diagnosis-aware Socratic hint prefix."""

from ilearn.agents.tutor import TutorAgent
from ilearn.core.schemas import AssessmentItem

_ITEM = AssessmentItem(
    id="t1",
    stem="12 + 8 = ?",
    type="fill",
    difficulty="easy",
    knowledge_ids=["addition"],
    answer_key="20",
    rubric_steps=["列竖式", "进位相加", "写答案"],
)


def test_socratic_hint_prefixes_strategy_for_calc_error():
    turn = TutorAgent().get_socratic_hint_with_diagnosis(
        _ITEM,
        "第二步不清楚",
        {"error_types": ["calc_error"]},
        phase="locate_gap",
        error_tag="calc_error",
    )
    assert "步骤引导" in turn.message
    assert "20" not in turn.message
    assert turn.phase == "hint_1"


def test_socratic_hint_prefixes_concept_gap():
    turn = TutorAgent().get_socratic_hint_with_diagnosis(
        _ITEM,
        "不懂概念",
        None,
        phase="locate_gap",
        error_tag="concept_gap",
    )
    assert "概念澄清" in turn.message
