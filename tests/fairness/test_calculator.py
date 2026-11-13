"""P7: fairness gap calculator."""

from __future__ import annotations

import pytest

from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.fairness.calculator import FairnessConfig, compute_fairness


@pytest.fixture
def learner_factory():
    def _make(*, mastery: dict[str, float]) -> LearnerState:
        m = {
            sid: MasteryEstimate(skill_id=sid, mastery=val, evidence_count=1)
            for sid, val in mastery.items()
        }
        return LearnerState(learner_id="x", mastery=m).seal_initial()

    return _make


@pytest.fixture
def attrs_factory():
    def _make(mapping: dict[str, dict]) -> dict[str, dict]:
        return dict(mapping)

    return _make


def test_mastery_gap_flagged(learner_factory, attrs_factory):
    high = [chr(ord("a") + i) for i in range(10)]
    low = [chr(ord("k") + i) for i in range(10)]
    learners = {
        **{k: learner_factory(mastery={"x": 0.9}) for k in high},
        **{k: learner_factory(mastery={"x": 0.3}) for k in low},
    }
    attrs = attrs_factory(
        {**{k: {"grade": "5"} for k in high}, **{k: {"grade": "6"} for k in low}}
    )
    report = compute_fairness(
        [],
        learners,
        attrs,
        "grade",
        cfg=FairnessConfig(min_group_size=10, mastery_gap_threshold=0.10),
    )
    assert any(c.metric == "mastery_mean" and c.flagged for c in report.comparisons)
