"""End-to-end verification of Composition Phase 2a diagnosis features."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_e2e_diagnosis_uses_evidence_log(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {}
    for index, item in enumerate(paper.items):
        if index < 3:
            answers[item.id] = "wrong-answer"
        else:
            answers[item.id] = item.answer_key or ""
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)

    assert completed.evidence_log
    assert completed.portrait is not None
    assert completed.portrait.mastery_records
    assert completed.diagnosis is not None
    assert completed.diagnosis.evidence_refs
    assert completed.diagnosis.interventions
    assert any(iv.evidence_ids for iv in completed.diagnosis.interventions)
    assert completed.portrait.mastery_records
    first_kid = next(iter(completed.portrait.mastery_records))
    assert completed.portrait.mastery_records[first_kid].evidence_count >= 1
    assert completed.plan is not None
