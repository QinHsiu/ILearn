"""P4: dispatch consumption match + SM-2 feedback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ilearn.core.learner_state import LearnerState
from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.feedback import apply_consumption
from ilearn.scheduler.matcher import ConsumptionMatcher
from ilearn.scheduler.models import ProactiveDispatchReceipt


@pytest.fixture
def now():
    return datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def receipt_factory(now):
    def _make(*, skill_ids: list[str], hours_ago: float = 2) -> ProactiveDispatchReceipt:
        return ProactiveDispatchReceipt(
            receipt_id=f"rcpt-{hours_ago}",
            learner_id="learner-1",
            trigger="spaced_repetition",
            reason="due",
            skill_ids=skill_ids,
            evidence_refs=["e1"],
            state_version=1,
            state_hash="abc",
            scheduled_at=now - timedelta(hours=hours_ago),
        ).seal()

    return _make


@pytest.fixture
def event_factory(now):
    def _make(etype: str, *, skill_id: str, accuracy: float = 0.8):
        return {
            "event_type": etype,
            "event_id": "evt-1",
            "skill_id": skill_id,
            "accuracy": accuracy,
            "occurred_at": now,
        }

    return _make


@pytest.fixture
def state_factory():
    def _make(**kwargs) -> LearnerState:
        review_meta = kwargs.pop("review_meta", {})
        review_schedule = kwargs.pop("review_schedule", {})
        # Allow nested dict shorthand from the design doc
        schedule: dict = {}
        meta: dict = dict(review_meta)
        for sid, val in review_schedule.items():
            if isinstance(val, dict):
                due = val.get("due_at") or datetime.now(timezone.utc)
                schedule[sid] = due
                meta[sid] = {
                    "interval_days": val.get("interval_days", 1.0),
                    "ease_factor": val.get("ease_factor", 2.5),
                    "review_count": val.get("review_count", 0),
                }
            else:
                schedule[sid] = val
        state = LearnerState(
            learner_id=kwargs.pop("learner_id", "learner-1"),
            review_schedule=schedule,
            review_meta=meta,
            engagement_signals=kwargs.pop("engagement_signals", {}),
            **kwargs,
        )
        return state.seal_initial()

    return _make


def test_match_responded_within_window(receipt_factory, event_factory):
    receipt = receipt_factory(skill_ids=["frac.add"], hours_ago=2)
    event = event_factory("practice.completed", skill_id="frac.add", accuracy=0.8)
    cons = ConsumptionMatcher([receipt]).match(event)
    assert cons is not None
    assert cons.outcome == "responded" and cons.quality == 4
    assert cons.receipt_id == receipt.receipt_id
    assert cons.evidence_refs == ["evt-1"]


def test_match_expired_outside_window(receipt_factory, event_factory):
    receipt = receipt_factory(skill_ids=["frac.add"], hours_ago=72)
    event = event_factory("practice.completed", skill_id="frac.add", accuracy=0.8)
    assert ConsumptionMatcher([receipt]).match(event) is None


def test_expire_overdue_emits_expired(receipt_factory, now):
    receipt = receipt_factory(skill_ids=["frac.add"], hours_ago=72)
    expired = ConsumptionMatcher([receipt]).expire_overdue(now=now)
    assert len(expired) == 1
    assert expired[0].outcome == "expired"
    assert expired[0].receipt_id == receipt.receipt_id


def test_apply_consumption_expired_resets_interval(state_factory, now):
    state = state_factory(
        review_schedule={"frac.add": {"interval_days": 10, "review_count": 3, "due_at": now}}
    )
    cons = DispatchConsumption(
        receipt_id="r1",
        learner_id=state.learner_id,
        outcome="expired",
        consumed_at=now,
        evidence_refs=[],
        skill_ids=["frac.add"],
    )
    new = apply_consumption(state, cons, receipt_state_version=state.version)
    assert new.review_meta["frac.add"]["review_count"] == 0
    assert new.review_meta["frac.add"]["interval_days"] == 1.0
    assert new.review_meta["frac.add"]["last_reset"] is True
    assert new.review_meta["frac.add"]["reset_reason"] == "dispatch_expired"
    assert new.review_schedule["frac.add"] == now
    # Source untouched (派生)
    assert state.review_meta["frac.add"]["review_count"] == 3


def test_apply_consumption_responded_updates_sm2(state_factory, now):
    state = state_factory(
        review_schedule={
            "frac.add": {
                "interval_days": 6.0,
                "review_count": 1,
                "ease_factor": 2.5,
                "due_at": now,
            }
        }
    )
    cons = DispatchConsumption(
        receipt_id="r1",
        learner_id=state.learner_id,
        outcome="responded",
        quality=5,
        consumed_at=now,
        skill_ids=["frac.add"],
    )
    new = apply_consumption(state, cons)
    assert new.review_meta["frac.add"]["review_count"] == 2
    assert new.version == state.version + 1


def test_consumption_replay_deterministic(state_factory, now):
    state = state_factory(
        review_schedule={"frac.add": {"interval_days": 1.0, "review_count": 0, "due_at": now}}
    )
    cons = DispatchConsumption(
        consumption_id="cons-fixed",
        receipt_id="r1",
        learner_id=state.learner_id,
        outcome="responded",
        quality=4,
        consumed_at=now,
        skill_ids=["frac.add"],
        evidence_refs=["e"],
    )
    a = apply_consumption(state, cons)
    b = apply_consumption(state, cons)
    assert a.state_hash == b.state_hash
    assert a.review_schedule == b.review_schedule
