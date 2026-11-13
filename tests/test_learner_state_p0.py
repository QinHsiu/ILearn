"""P0: versioned LearnerState + projection + cross-session continuity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ilearn.core.learner_bridge import events_from_diagnosis, resolve_learner_id
from ilearn.core.learner_state import LearnerState
from ilearn.core.projection import project, verify_chain
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionPhase,
    SessionState,
    StudentProfile,
)
from ilearn.core.state_event import StateEvent
from ilearn.storage.learner_state_store import LearnerStateStore


def test_hash_chain_project_roundtrip():
    initial = LearnerState(learner_id="nick:alice").seal_initial()
    e1 = StateEvent(
        learner_id="nick:alice",
        event_type="mastery.update",
        payload={"skill_id": "frac", "mastery": 0.4},
        prev_state_hash=initial.state_hash,
    ).seal()
    s1 = initial.apply(e1)
    e2 = StateEvent(
        learner_id="nick:alice",
        event_type="misconception.detected",
        payload={"code": "concept_gap", "description": "分数通分"},
        prev_state_hash=s1.state_hash,
    ).seal()
    final = project([e1, e2], initial)
    assert final.version == 2
    assert final.mastery["frac"].mastery == 0.4
    assert final.misconceptions[0].code == "concept_gap"
    assert verify_chain([e1, e2], initial)


def test_broken_chain_raises():
    initial = LearnerState(learner_id="x").seal_initial()
    bad = StateEvent(
        learner_id="x",
        event_type="mastery.update",
        payload={"skill_id": "a", "mastery": 0.1},
        prev_state_hash="deadbeef",
    ).seal()
    try:
        project([bad], initial)
        assert False, "expected AssertionError"
    except AssertionError:
        pass


def test_store_persists_across_reload(tmp_path: Path):
    store = LearnerStateStore(tmp_path / "learners")
    lid = "nick:bob"
    s0 = store.load(lid)
    store.append(
        lid,
        StateEvent(
            learner_id=lid,
            event_type="goal.set",
            payload={"goal": "掌握分数加减"},
            prev_state_hash=s0.state_hash,
        ),
    )
    store.append(
        lid,
        StateEvent(
            learner_id=lid,
            event_type="mastery.update",
            payload={"skill_id": "frac_add", "mastery": 0.55},
        ),
    )
    # Simulate "one week later" — new store instance, same disk
    store2 = LearnerStateStore(tmp_path / "learners")
    again = store2.load(lid)
    assert again.version >= 2
    assert again.goals == ["掌握分数加减"]
    assert again.mastery["frac_add"].mastery == 0.55
    assert again.state_hash


def test_two_sessions_consume_same_projected_state(tmp_path: Path):
    """Acceptance: Diagnosis/Planning inputs share folded LearnerState across sessions."""
    store = LearnerStateStore(tmp_path / "learners")
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="cara")
    lid = resolve_learner_id(profile)

    session1 = SessionState(
        session_id="s1",
        profile=profile,
        phase=SessionPhase.DIAGNOSE,
        diagnosis=DiagnosisReport(
            curriculum_label="北京·人教",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="k_frac",
                    knowledge_name="分数",
                    level="weak",
                    score_rate=0.3,
                    error_tag_counts={"concept_gap": 2},
                )
            ],
        ),
    )
    for ev in events_from_diagnosis(session1):
        store.append(lid, ev)
    state_week0 = store.load(lid)

    # Week later: second session reads same projection before any new write
    state_week1 = LearnerStateStore(tmp_path / "learners").load(lid)
    assert state_week1.state_hash == state_week0.state_hash
    assert state_week1.version == state_week0.version
    assert state_week1.mastery["k_frac"].mastery == 0.3
    assert any(m.code == "concept_gap" for m in state_week1.misconceptions)
