"""End-to-end verification of the multi-agent P0 pipeline (offline)."""

from pathlib import Path

from ilearn.core.orchestrator import Orchestrator
from ilearn.core.schemas import SessionPhase, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> Orchestrator:
    return Orchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )


def test_e2e_beijing_grade5_offline_loop(tmp_path):
    """Full multi-agent path including optional follow-up when weak items injected."""
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))

    assert orch.current_phase(sid) == SessionPhase.ONBOARD

    paper = orch.generate_assessment(sid)
    assert len(paper.items) == 20
    assert orch.current_phase(sid) == SessionPhase.PRACTICE

    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    session = orch.run_after_submit(sid)

    assert len(session.grades) == 20
    assert session.diagnosis is not None
    assert session.plan is not None
    assert session.portrait is not None
    assert session.portrait.student_key
    assert session.loop_count <= 2
    assert "课标依据" in session.plan.markdown or session.plan is not None
    assert session.phase in {SessionPhase.PLAN, SessionPhase.PRACTICE}
    assert "学习计划" in orch.report(sid) or "计划" in orch.report(sid)


def test_e2e_beijing_grade5_offline_weak_followup(tmp_path):
    """Weak diagnostic results trigger a targeted follow-up paper (loop_count >= 1)."""
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)

    orch.submit(sid, {item.id: "wrong" for item in paper.items})
    session = orch.run_after_submit(sid)

    assert session.portrait is not None
    assert session.diagnosis is not None
    assert session.plan is not None
    assert "课标依据" in session.plan.markdown or session.plan is not None
    assert 1 <= session.loop_count <= 2
    assert session.phase == SessionPhase.PRACTICE
    assert session.paper is not None
    assert 1 <= len(session.paper.items) <= 10
