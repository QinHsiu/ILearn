"""Companion evaluate action actually starts assessment."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


def test_companion_evaluate_generates_paper(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    store = SessionStore(tmp_path / "sessions")
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(pilot),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    reply = orch.companion_chat(sid, message="给我出一套测评卷")
    assert reply.intent == "evaluate"
    assert any(a.type == "start_assessment" for a in reply.actions)
    session = store.load(sid)
    assert session.paper is not None
    assert len(session.paper.items) >= 1


def test_companion_evaluate_grade7_degrades_without_crash(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    store = SessionStore(tmp_path / "sessions")
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(pilot),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=7, age=13))
    reply = orch.companion_chat(sid, message="给我出一套测评卷")
    assert reply.intent == "evaluate"
    assert not any(a.type == "start_assessment" for a in reply.actions)
    assert "4" in reply.reply or "试点" in reply.reply
    assert store.load(sid).paper is None
