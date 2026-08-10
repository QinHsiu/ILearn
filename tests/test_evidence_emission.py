from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_full_loop_populates_evidence_log(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    completed = orch.run_after_submit(sid)
    assert len(completed.evidence_log) >= 1
    assert completed.evidence_log[0].session_id == sid
