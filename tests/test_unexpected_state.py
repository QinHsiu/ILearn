"""UNEXPECTED_STATE capture + resume decision."""

from __future__ import annotations

from pathlib import Path

from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.orchestration.unexpected import (
    list_unexpected_events,
    record_unexpected_state,
    resume_session,
)


def test_record_unexpected_state_writes_event_and_checkpoint(tmp_path: Path):
    session = SessionState(
        session_id="s-ux-1",
        profile=StudentProfile(region="北京", grade=5, age=11),
        phase=SessionPhase.PRACTICE,
    )
    event = record_unexpected_state(
        session,
        checkpoint_dir=tmp_path,
        context={"raw_input": "这题和奥数有关吗", "item_id": "q9"},
        stage=SessionPhase.PRACTICE,
        agent="tutor",
    )
    assert event.kind == "unexpected_state"
    assert any(e.kind == "unexpected_state" for e in session.event_log)
    checkpoint = tmp_path / "s-ux-1.unexpected.json"
    assert checkpoint.exists()


def test_resume_session_appends_resume_event(tmp_path: Path):
    session = SessionState(
        session_id="s-ux-2",
        profile=StudentProfile(region="北京", grade=5, age=11),
        phase=SessionPhase.PRACTICE,
    )
    record_unexpected_state(
        session,
        checkpoint_dir=tmp_path,
        context={"raw_input": "???"},
        stage=SessionPhase.PRACTICE,
        agent="tutor",
    )
    resume_session(session, decision="continue", note="teacher reviewed")
    kinds = [e.kind for e in session.event_log]
    assert "unexpected_state" in kinds
    assert "resume" in kinds
    assert list_unexpected_events(session)
