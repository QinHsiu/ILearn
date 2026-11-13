"""P10: experience-strategy feedback weights."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.experience.feedback_weights import ExperienceFeedbackRouter
from ilearn.experience.models import ExperienceRecord
from ilearn.experience.store import ExperienceStore


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def record_factory(now):
    def _make(strategy: str, outcome: str, n: int = 1):
        return [
            ExperienceRecord(
                record_id=f"{strategy}-{i}",
                learner_segment={"stage": "k12", "skill": "frac"},
                situation="hint_before_attempt",
                structural_signature=["diagnose:low", "hint:1"],
                strategy=strategy,
                outcome=outcome,  # type: ignore[arg-type]
                form="episodic",
                evidence_refs=[f"e-{i}"],
                created_at=now,
                state_version_at_creation=10,
            )
            for i in range(n)
        ]

    return _make


def test_repeated_negative_drives_weight_down():
    router = ExperienceFeedbackRouter()
    for _ in range(20):
        router.observe("hint_level_3", "negative")
    assert router.get_weight("hint_level_3") < 0.5


def test_mixed_feedback_stays_neutral():
    router = ExperienceFeedbackRouter()
    for _ in range(10):
        router.observe("hint_level_2", "positive")
        router.observe("hint_level_2", "negative")
    assert 0.4 < router.get_weight("hint_level_2") < 0.6



def test_feedback_affects_retrieval_ranking(record_factory, now):
    router = ExperienceFeedbackRouter()
    for _ in range(20):
        router.observe("hint_level_3", "negative")
    store = ExperienceStore(
        record_factory("hint_level_3", "effective", n=4), feedback=router
    )
    prior = store.retrieve(
        {"stage": "k12", "skill": "frac"},
        "hint_before_attempt",
        current_state_version=10,
        now=now,
    )
    assert prior is not None
    assert prior.confidence < 0.5
