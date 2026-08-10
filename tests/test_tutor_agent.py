"""Failing tests for TutorAgent Socratic state machine — run before implementation."""

from ilearn.agents.tutor import TutorAgent
from ilearn.core.schemas import AssessmentItem, TutorPhase

_ITEM = AssessmentItem(
    id="t1",
    stem="12 + 8 = ?",
    type="fill",
    difficulty="easy",
    knowledge_ids=["addition"],
    answer_key="20",
    rubric_steps=["列竖式", "进位相加", "写答案"],
)


def test_tutor_start_does_not_leak_answer():
    turn = TutorAgent().start(_ITEM, "calc_error")
    assert "20" not in turn.message
    assert turn.phase == "locate_gap"


def test_tutor_escalates_locate_to_hint1():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("locate_gap", "第二步进位不清楚", _ITEM)
    assert turn.phase == "hint_1"
    assert "20" not in turn.message


def test_tutor_escalates_hint1_to_hint2():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("hint_1", "还是不太懂", _ITEM)
    assert turn.phase == "hint_2"
    assert "20" not in turn.message


def test_tutor_escalates_hint2_to_retry():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("hint_2", "明白了", _ITEM)
    assert turn.phase == "retry"
    assert "20" not in turn.message


def test_tutor_retry_success_goes_done():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("retry", "我算出来了，步骤对了", _ITEM)
    assert turn.phase == "done"
    assert "20" not in turn.message


def test_tutor_retry_failure_goes_explain():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("retry", "", _ITEM)
    assert turn.phase == "explain"
    assert "20" not in turn.message


def test_tutor_retry_wrong_keywords_goes_explain():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("retry", "还是不对，不会", _ITEM)
    assert turn.phase == "explain"
    assert "20" not in turn.message


def test_tutor_explain_never_leaks_answer():
    agent = TutorAgent()
    agent.start(_ITEM, "calc_error")
    turn = agent.step("explain", "请讲解", _ITEM)
    assert turn.phase == "done"
    assert "20" not in turn.message


def test_tutor_all_phases_never_leak_answer_key():
    agent = TutorAgent()
    item = _ITEM.model_copy(update={"answer_key": "SECRET99"})
    phases: list[TutorPhase] = ["locate_gap", "hint_1", "hint_2", "retry", "explain"]
    turn = agent.start(item, "concept_gap")
    assert "SECRET99" not in turn.message
    for phase in phases:
        turn = agent.step(phase, "学生回复", item)
        assert "SECRET99" not in turn.message, f"leaked in phase {turn.phase}"
