"""Edition 0830_6 D — KG hard-fail, confidence, hint outcome, calm tutor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.tutor import TutorAgent, _CALM_PREFIX
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.core.schemas import (
    AssessmentItem,
    GradeResult,
    HintInteraction,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_knowledge_graph_hard_fails_on_cycle(tmp_path: Path):
    path = tmp_path / "kg.json"
    path.write_text(
        json.dumps(
            {
                "a": {"prerequisites": ["b"], "related": [], "grade": 5},
                "b": {"prerequisites": ["a"], "related": [], "grade": 5},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="circular"):
        KnowledgeGraph(path, strict_cycles=True)


def test_knowledge_graph_warns_but_loads_with_cycles(tmp_path: Path):
    path = tmp_path / "kg.json"
    path.write_text(
        json.dumps(
            {
                "a": {"prerequisites": ["b"], "related": [], "grade": 5},
                "b": {"prerequisites": ["a"], "related": [], "grade": 5},
            }
        ),
        encoding="utf-8",
    )
    g = KnowledgeGraph(path, strict_cycles=False)
    assert g.cycle_count >= 1
    assert g.get_prerequisites("a") == ["b"]


def test_diagnosis_confidence_scales_with_volume():
    low = DiagnosisAgent._compute_diagnosis_confidence([], [], "insufficient_data")
    assert low["score"] < 0.3
    mid = DiagnosisAgent._compute_diagnosis_confidence(
        [object(), object()], [], "limited_data"
    )
    assert 0.3 <= mid["score"] <= 0.55
    grades = [
        GradeResult(
            item_id=f"i{i}",
            final_correct=True,
            knowledge_ids=["frac_add_same"],
        )
        for i in range(8)
    ]
    high = DiagnosisAgent._compute_diagnosis_confidence(grades, grades, "ok")
    assert high["score"] >= 0.6


def test_hint_effectiveness_summary():
    summary = DiagnosisAgent._summarize_hint_effectiveness(
        {
            "i1": [
                {"solved_after_hint": True},
                {"solved_after_hint": False},
            ]
        }
    )
    assert summary["hint_turns_scored"] == 2
    assert summary["solved_after_hint_rate"] == 0.5


def test_update_hint_outcomes_from_grades():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
        grades=[
            GradeResult(
                item_id="q1",
                final_correct=True,
                knowledge_ids=[],
            )
        ],
        hint_interactions={
            "q1": [
                HintInteraction(
                    item_id="q1", turn=1, user_input="不会", ai_hint="先审题"
                )
            ]
        },
    )
    MultiAgentOrchestrator._update_hint_outcomes(session)
    assert session.hint_interactions["q1"][0].solved_after_hint is True


def test_tutor_calm_tone_when_frustrated():
    agent = TutorAgent()
    item = AssessmentItem(
        id="i1",
        stem="q",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
        answer_key="1",
    )
    calm = agent.start(item, None, frustration=0.5)
    assert _CALM_PREFIX in calm.message
    normal = agent.start(item, None, frustration=0.0)
    assert _CALM_PREFIX not in normal.message


def test_grade_writes_solved_after_hint(tmp_path: Path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    item = paper.items[0]
    orch.tutor_start(sid, item.id)
    orch.tutor_step(sid, item.id, "不会")
    orch.submit(
        sid, {row.id: (row.answer_key or "x") for row in paper.items}
    )
    orch.grade(sid)
    session = orch._store.load(sid)
    rows = session.hint_interactions.get(item.id) or []
    assert rows
    assert rows[0].solved_after_hint is not None
