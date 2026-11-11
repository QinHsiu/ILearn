"""Tutor done-phase input triggers UNEXPECTED_STATE + checkpoint."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import SessionPhase, StudentProfile, TutorTurn
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


def test_tutor_step_after_done_records_unexpected(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    store = SessionStore(tmp_path / "sessions")
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(pilot),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    item = paper.items[0]
    answers = {row.id: (row.answer_key or "") for row in paper.items}
    orch.submit(sid, answers)
    orch.grade(sid)

    session = store.load(sid)
    session.phase = SessionPhase.PRACTICE
    session.tutor_by_item[item.id] = TutorTurn(
        phase="done",
        message="辅导已结束。",
        error_tag=None,
    )
    store.save(session)

    turn = orch.tutor_step(sid, item.id, "那奥数题怎么做")
    session = store.load(sid)
    assert any(e.kind == "unexpected_state" for e in session.event_log)
    assert "脱轨" in turn.message or "暂停" in turn.message or "老师" in turn.message
    checkpoint = tmp_path / "sessions" / "checkpoints" / f"{sid}.unexpected.json"
    assert checkpoint.exists()
