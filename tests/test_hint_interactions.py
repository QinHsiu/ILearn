from pathlib import Path

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import HintInteraction, MAX_HINTS_PER_ITEM, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_hint_interaction_fields():
    row = HintInteraction(item_id="q1", turn=1, user_input="不会", ai_hint="先写已知")
    assert row.item_id == "q1"
    assert row.has_image is False
    assert row.solved_after_hint is None


def test_tutor_start_during_assess_without_grades(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    item_id = paper.items[0].id
    turn = orch.tutor_start(sid, item_id)
    assert turn.message
    session = orch._store.load(sid)
    assert item_id in session.tutor_by_item
    assert session.hint_interactions.get(item_id, []) == []


def test_tutor_hint_limit_three(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    item_id = paper.items[0].id
    orch.tutor_start(sid, item_id)
    for i in range(MAX_HINTS_PER_ITEM):
        orch.tutor_step(sid, item_id, f"困惑{i}")
    session = orch._store.load(sid)
    assert len(session.hint_interactions[item_id]) == MAX_HINTS_PER_ITEM
    with pytest.raises(ValueError, match="exhausted"):
        orch.tutor_step(sid, item_id, "第四次")
