from pathlib import Path

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import PlanVersion, StudentProfile
from ilearn.core.user_errors import UserFriendlyError
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )


def _session_with_plan(orch: MultiAgentOrchestrator) -> str:
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    orch.run_after_submit(sid)
    return sid


def test_request_replan_appends_plan_history(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = _session_with_plan(orch)
    session_before = orch._store.load(sid)
    assert session_before.plan is not None
    first_version = session_before.plan.version

    replanned = orch.request_replan(sid)
    session_after = orch._store.load(sid)

    assert replanned.version == first_version + 1
    assert session_after.plan is not None
    assert session_after.plan.version == first_version + 1
    assert len(session_after.plan_history) >= 1
    assert session_after.plan_history[-1].status == "superseded"
    assert session_after.plan_history[-1].version == first_version
    assert isinstance(session_after.plan_history[-1], PlanVersion)


def test_request_replan_requires_diagnosis(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    orch.generate_assessment(sid)
    with pytest.raises(UserFriendlyError) as exc:
        orch.request_replan(sid)
    assert exc.value.code == "E-013"


def test_tutor_start_returns_locate_gap_without_answer(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {}
    for index, item in enumerate(paper.items):
        if index == 0:
            answers[item.id] = "wrong"
        else:
            answers[item.id] = item.answer_key or ""
    orch.submit(sid, answers)
    orch.run_after_submit(sid)

    session = orch._store.load(sid)
    wrong_grade = next(g for g in session.grades if not g.final_correct)
    item = next(i for i in session.paper.items if i.id == wrong_grade.item_id)

    turn = orch.tutor_start(sid, item.id)
    assert turn.phase == "locate_gap"
    if item.answer_key:
        assert item.answer_key not in turn.message
