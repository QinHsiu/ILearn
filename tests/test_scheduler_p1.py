"""P1: SM-2 + proactive dispatch receipts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.core.state_event import StateEvent
from ilearn.scheduler.dispatcher import build_review_events_from_mastery, due_dispatches
from ilearn.scheduler.spaced_repetition import SM2State, sm2_update
from ilearn.storage.learner_state_store import LearnerStateStore


def test_sm2_pure_update():
    s0 = SM2State()
    s1 = sm2_update(s0, 4)
    assert s1.review_count == 1
    assert s1.interval_days == 1.0
    s2 = sm2_update(s1, 5)
    assert s2.interval_days == 6.0
    fail = sm2_update(s2, 1)
    assert fail.review_count == 0
    assert fail.interval_days == 1.0


def test_due_receipt_has_evidence_and_hash(tmp_path: Path):
    store = LearnerStateStore(tmp_path / "learners")
    lid = "nick:due"
    now = datetime.now(timezone.utc)
    state = store.load(lid)
    store.append(
        lid,
        StateEvent(
            learner_id=lid,
            event_type="mastery.update",
            payload={"skill_id": "frac", "mastery": 0.5},
            prev_state_hash=state.state_hash,
        ),
    )
    state = store.load(lid)
    # Force due in the past
    store.append(
        lid,
        StateEvent(
            learner_id=lid,
            event_type="review.scheduled",
            payload={
                "skill_id": "frac",
                "due_at": (now - timedelta(hours=1)).isoformat(),
            },
        ),
    )
    state = store.load(lid)
    receipts = due_dispatches(state, now=now)
    assert receipts
    r = receipts[0]
    assert r.trigger == "spaced_repetition"
    assert r.evidence_refs
    assert r.state_version == state.version
    assert r.receipt_hash
    assert r.reason


def test_build_review_events():
    state = LearnerState(
        learner_id="n",
        mastery={
            "a": MasteryEstimate(skill_id="a", mastery=0.7, evidence_count=2),
        },
    ).seal_initial()
    events = build_review_events_from_mastery(state)
    assert len(events) == 1
    assert events[0].event_type == "review.scheduled"
    assert events[0].payload["skill_id"] == "a"
