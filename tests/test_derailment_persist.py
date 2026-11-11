"""Derailment report can be persisted as a snapshot file."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.orchestration.events import append_orchestration_event
from ilearn.orchestration.unexpected import derailment_report, persist_derailment_report


def test_persist_derailment_report(tmp_path: Path):
    session = SessionState(
        session_id="d1",
        profile=StudentProfile(region="北京", grade=5, age=11),
        phase=SessionPhase.PRACTICE,
    )
    append_orchestration_event(
        session,
        agent="tutor",
        stage=SessionPhase.PRACTICE,
        reason="UNEXPECTED_STATE",
        kind="unexpected_state",
        ok=False,
        metadata={"knowledge_id": "dec_mult"},
    )
    report = derailment_report([session])
    path = persist_derailment_report(tmp_path, report)
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["total_unexpected"] == 1
    assert loaded["by_knowledge"]["dec_mult"] == 1
