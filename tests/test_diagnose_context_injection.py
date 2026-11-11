"""Orchestrator diagnose injects context_messages for compaction."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


def test_diagnose_stores_context_compaction(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    store = SessionStore(tmp_path / "sessions")
    orch = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(pilot),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    orch.grade(sid)
    orch.diagnose(sid)
    session = store.load(sid)
    enrichment = session.metadata.get("diagnosis_enrichment") or {}
    assert "context_compaction" in enrichment
    assert enrichment["context_compaction"]["message_count"] >= 1
