"""ExperienceStore retrieve / extractor (P2)."""

from __future__ import annotations

import pytest

from ilearn.experience.extractor import extract_experiences
from ilearn.experience.models import ExperienceRecord
from ilearn.experience.store import ExperienceStore


@pytest.fixture
def record_factory():
    def _make(strategy: str, outcome: str, n: int = 1, skill: str = "frac"):
        return [
            ExperienceRecord(
                record_id=f"{strategy}-{outcome}-{i}",
                learner_segment={"stage": "k12", "skill": skill},
                situation="hint_before_attempt",
                strategy=strategy,
                outcome=outcome,  # type: ignore[arg-type]
                evidence_refs=[f"e-{i}"],
            )
            for i in range(n)
        ]

    return _make


@pytest.fixture
def sample_events():
    return [
        {
            "event_type": "tutoring.hint",
            "event_id": "h1",
            "session_id": "s1",
            "trigger": "hint",
            "phase": "attempt",
            "hint_level": 2,
        },
        {
            "event_type": "grade.completed",
            "event_id": "g1",
            "session_id": "s1",
            "life_stage": "k12",
            "grade": 5,
            "skill_id": "frac",
            "score": 0.9,
            "occurred_at": "2026-11-13T00:00:00+00:00",
        },
    ]


def test_retrieve_requires_min_support(record_factory):
    store = ExperienceStore(record_factory("hint_level_2", "effective", n=2))
    assert (
        store.retrieve({"stage": "k12", "skill": "frac"}, "hint_before_attempt")
        is None
    )


def test_retrieve_picks_effective_strategy(record_factory):
    records = record_factory("hint_level_1", "effective", n=4) + record_factory(
        "hint_level_3", "ineffective", n=4
    )
    prior = ExperienceStore(records).retrieve(
        {"stage": "k12", "skill": "frac"}, "hint_before_attempt"
    )
    assert prior is not None
    assert prior.recommended_strategy == "hint_level_1"
    assert prior.confidence > 0
    assert prior.experience_refs


def test_extractor_links_hint_to_outcome(sample_events):
    records = extract_experiences(sample_events)
    assert all(r.evidence_refs for r in records)
    assert any(r.outcome == "effective" for r in records)
