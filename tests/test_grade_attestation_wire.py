"""Practice grading persists attestation_log beside the session store."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


def test_grade_writes_attestation_log(tmp_path: Path):
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
    grades = orch.grade(sid)
    assert grades
    attestation = (tmp_path / "sessions" / "attestations" / sid / "attestation_log.jsonl")
    assert attestation.is_file()
    lines = [ln for ln in attestation.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
