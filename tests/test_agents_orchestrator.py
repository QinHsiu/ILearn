from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import SessionPhase, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )


def test_multi_agent_full_loop_offline(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))

    assert orch.current_phase(sid) == SessionPhase.ONBOARD
    paper = orch.generate_assessment(sid)
    assert len(paper.items) == 20
    assert orch.current_phase(sid) == SessionPhase.PRACTICE

    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    assert orch.current_phase(sid) == SessionPhase.GRADE

    completed = orch.run_after_submit(sid)

    assert len(completed.grades) == 20
    assert completed.diagnosis is not None
    assert completed.plan is not None
    assert completed.portrait is not None
    assert completed.phase == SessionPhase.PLAN
    assert "课标依据" in completed.plan.markdown
    # C2: first-pass diagnostic grading (loop_count == 0) is unassisted evidence.
    assert all(g.lane == "probe" for g in completed.grades)
    assert completed.evidence_log
    assert all(e.lane == "probe" for e in completed.evidence_log)


def test_submit_fills_missing_answers_before_practice_agent_grades(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)

    orch.submit(sid, {paper.items[0].id: paper.items[0].answer_key or ""})
    grades = orch.grade(sid)

    assert len(grades) == 20
    assert {grade.item_id for grade in grades} == {item.id for item in paper.items}
    assert sum(grade.final_correct for grade in grades) == 1


def test_run_after_submit_starts_followup_for_weak_results(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)

    orch.submit(sid, {})
    completed = orch.run_after_submit(sid)

    assert completed.loop_count == 1
    assert completed.phase == SessionPhase.PRACTICE
    assert completed.paper is not None
    assert 1 <= len(completed.paper.items) <= 10
    assert completed.answers == []
    assert completed.image_answers == []
    assert completed.grades == []
    assert completed.diagnosis is not None
    assert completed.plan is not None
    assert completed.portrait is not None


def test_session_store_round_trips_multi_agent_fields(tmp_path):
    store = SessionStore(tmp_path)
    state = store.create(StudentProfile(region="北京", grade=5, age=11))
    state.phase = SessionPhase.PRACTICE_LOOP
    state.loop_count = 1

    saved = store.save(state)

    assert store.load(saved.session_id) == saved
