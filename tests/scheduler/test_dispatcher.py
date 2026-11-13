"""Scheduler.scan + receipt verify/replay (P1)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.scheduler.dispatcher import Scheduler
from ilearn.scheduler.replay import verify_receipt


class FakeEventLog:
    def __init__(self) -> None:
        self.rows: list[tuple[str, dict, str]] = []

    def append(self, event_type: str, payload: dict, learner_id: str) -> str:
        self.rows.append((event_type, payload, learner_id))
        return f"evt-{len(self.rows)}"


@pytest.fixture
def fake_event_log():
    return FakeEventLog()


@pytest.fixture
def learner_state_factory():
    def _make(**kwargs) -> LearnerState:
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        mastery = kwargs.pop("mastery", None)
        if mastery is None:
            mastery = {
                "frac.add": MasteryEstimate(
                    skill_id="frac.add", mastery=0.6, evidence_count=2, last_updated=now
                )
            }
        state = LearnerState(
            learner_id=kwargs.pop("learner_id", "learner-1"),
            mastery=mastery,
            review_schedule=kwargs.pop("review_schedule", {}),
            review_meta=kwargs.pop("review_meta", {}),
            engagement_signals=kwargs.pop(
                "engagement_signals", {"consecutive_inactive_days": 0}
            ),
            **kwargs,
        )
        return state.seal_initial()

    return _make


def test_scan_emits_receipt_for_due_items(fake_event_log, learner_state_factory):
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)
    state = learner_state_factory(
        review_schedule={"frac.add": now.replace(day=10)},
        engagement_signals={"consecutive_inactive_days": 0},
    )
    receipts = Scheduler(fake_event_log, clock=lambda: now).scan(state)
    assert len(receipts) == 1
    assert receipts[0].trigger == "spaced_repetition"
    assert receipts[0].state_version == state.version
    assert receipts[0].evidence_refs
    assert verify_receipt(receipts[0])
    assert fake_event_log.rows
    assert fake_event_log.rows[0][0] == "scheduler.dispatch"


def test_receipt_tamper_detection(fake_event_log, learner_state_factory):
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)
    state = learner_state_factory(review_schedule={"a": now})
    receipt = Scheduler(fake_event_log, clock=lambda: now).scan(state)[0]
    receipt.reason = "tampered"
    assert not verify_receipt(receipt)


def test_engagement_drop_bypass(fake_event_log, learner_state_factory):
    now = datetime(2026, 11, 13, tzinfo=timezone.utc)
    state = learner_state_factory(
        review_schedule={},
        engagement_signals={"consecutive_inactive_days": 5},
    )
    receipts = Scheduler(fake_event_log, clock=lambda: now).scan(state)
    assert any(r.trigger == "engagement_drop" for r in receipts)
