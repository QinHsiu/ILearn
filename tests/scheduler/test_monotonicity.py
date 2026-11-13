"""P4-deep: version monotonicity + explicit expired reset."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.core.learner_state import LearnerState
from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.feedback import StateInvariantError, apply_consumption


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def state_factory(now):
    def _make(*, version: int = 0, review_schedule=None) -> LearnerState:
        schedule = {}
        meta = {}
        for sid, val in (review_schedule or {}).items():
            if isinstance(val, dict):
                schedule[sid] = val.get("due_at") or now
                meta[sid] = {
                    k: v for k, v in val.items() if k != "due_at"
                }
            else:
                schedule[sid] = val
        state = LearnerState(
            learner_id="L1",
            version=version,
            review_schedule=schedule,
            review_meta=meta,
        )
        sealed = state.seal_initial()
        # seal_initial forces version=0; restore requested version for assertion tests
        sealed.version = version
        sealed.state_hash = sealed.compute_hash()
        return sealed

    return _make


@pytest.fixture
def consumption_factory(now):
    def _make(
        *,
        receipt_state_version: int = 0,
        outcome: str = "responded",
        quality: int | None = 4,
        skill_ids: list[str] | None = None,
    ) -> DispatchConsumption:
        return DispatchConsumption(
            receipt_id="r1",
            learner_id="L1",
            outcome=outcome,  # type: ignore[arg-type]
            quality=quality,
            consumed_at=now,
            skill_ids=skill_ids or ["frac.add"],
            trigger="spaced_repetition",
            receipt_state_version=receipt_state_version,
        )

    return _make


def test_consumption_advances_version(state_factory, consumption_factory):
    state = state_factory(version=5)
    cons = consumption_factory(receipt_state_version=5)
    assert apply_consumption(state, cons, receipt_state_version=5).version == 6


def test_consumption_rejects_version_regression(state_factory, consumption_factory):
    state = state_factory(version=5)
    cons = consumption_factory(receipt_state_version=10)
    with pytest.raises(StateInvariantError):
        apply_consumption(state, cons, receipt_state_version=10)


def test_expired_marks_reset_not_silent(state_factory, consumption_factory):
    state = state_factory(
        version=3,
        review_schedule={"frac.add": {"interval_days": 10, "review_count": 3}},
    )
    cons = consumption_factory(outcome="expired", quality=None, receipt_state_version=3)
    new = apply_consumption(state, cons, receipt_state_version=state.version)
    assert new.review_meta["frac.add"]["last_reset"] is True
    assert new.review_meta["frac.add"]["reset_reason"] == "dispatch_expired"
