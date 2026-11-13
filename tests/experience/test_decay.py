"""P5: experience time/version decay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ilearn.experience.decay import DecayConfig, time_weight
from ilearn.experience.models import ExperienceRecord
from ilearn.experience.store import ExperienceStore


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def record_factory(now):
    def _make(
        strategy: str,
        outcome: str,
        *,
        days_ago: float,
        state_version: int,
        n: int = 1,
        skill: str = "frac",
    ):
        created = now - timedelta(days=days_ago)
        return [
            ExperienceRecord(
                record_id=f"{strategy}-{outcome}-{i}",
                learner_segment={"stage": "k12", "skill": skill},
                situation="hint_before_attempt",
                strategy=strategy,
                outcome=outcome,  # type: ignore[arg-type]
                evidence_refs=[f"e-{i}"],
                created_at=created,
                state_version_at_creation=state_version,
            )
            for i in range(n)
        ]

    return _make


def test_time_weight_half_life():
    cfg = DecayConfig(half_life_days=90)
    assert abs(time_weight(90, cfg) - 0.5) < 1e-9
    assert time_weight(0, cfg) == 1.0


def test_old_effective_decays_below_recent_neutral(record_factory, now):
    old = record_factory("hint_l2", "effective", days_ago=180, state_version=1, n=4)
    recent = record_factory("hint_l1", "neutral", days_ago=5, state_version=10, n=4)
    prior = ExperienceStore(old + recent).retrieve(
        {"stage": "k12", "skill": "frac"},
        "hint_before_attempt",
        current_state_version=10,
        now=now,
    )
    assert prior is not None
    assert prior.support == 4
    assert prior.recency_score < 0.5
    assert prior.weighted_confidence >= 0


def test_version_distance_penalizes(record_factory, now):
    stale = record_factory("hint_l2", "effective", days_ago=10, state_version=0, n=4)
    fresh = record_factory("hint_l1", "effective", days_ago=10, state_version=9, n=4)
    prior = ExperienceStore(stale + fresh).retrieve(
        {"stage": "k12", "skill": "frac"},
        "hint_before_attempt",
        current_state_version=10,
        now=now,
    )
    assert prior is not None
    assert prior.recommended_strategy == "hint_l1"
    assert prior.version_distance == 1
