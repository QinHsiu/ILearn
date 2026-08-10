"""End-to-end verification of Composition Optimization Phase 1 features."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_e2e_phase1_offline_beijing_g5(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    assert paper.blueprint is not None
    assert len(paper.blueprint.slots) == 20
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)
    assert completed.evidence_log
    assert completed.portrait.mastery_records or completed.portrait.knowledge_state
    assert completed.plan is not None
    assert "课标依据" in completed.plan.markdown
    assert completed.grades[0].receipt is not None
