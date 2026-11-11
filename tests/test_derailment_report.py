"""Aggregate UNEXPECTED_STATE events into a derailment report."""

from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.orchestration.events import append_orchestration_event
from ilearn.orchestration.unexpected import derailment_report


def test_derailment_report_groups_by_grade_and_stage():
    sessions = [
        SessionState(
            session_id="a",
            profile=StudentProfile(region="北京", grade=5, age=11),
            phase=SessionPhase.PRACTICE,
        ),
        SessionState(
            session_id="b",
            profile=StudentProfile(region="北京", grade=5, age=11),
            phase=SessionPhase.PRACTICE,
        ),
        SessionState(
            session_id="c",
            profile=StudentProfile(region="北京", grade=6, age=12),
            phase=SessionPhase.PRACTICE,
        ),
    ]
    append_orchestration_event(
        sessions[0],
        agent="tutor",
        stage=SessionPhase.PRACTICE,
        reason="UNEXPECTED_STATE",
        kind="unexpected_state",
        ok=False,
        metadata={"knowledge_id": "dec_mult"},
    )
    append_orchestration_event(
        sessions[1],
        agent="tutor",
        stage=SessionPhase.PRACTICE,
        reason="UNEXPECTED_STATE",
        kind="unexpected_state",
        ok=False,
        metadata={"knowledge_id": "dec_mult"},
    )
    append_orchestration_event(
        sessions[2],
        agent="tutor",
        stage=SessionPhase.GRADE,
        reason="UNEXPECTED_STATE",
        kind="unexpected_state",
        ok=False,
        metadata={"knowledge_id": "frac_add"},
    )
    report = derailment_report(sessions)
    assert report["total_unexpected"] == 3
    assert report["by_grade"]["5"] == 2
    assert report["by_grade"]["6"] == 1
    assert report["by_stage"]["practice"] == 2
    assert report["by_stage"]["grade"] == 1
    assert report["by_knowledge"]["dec_mult"] == 2
