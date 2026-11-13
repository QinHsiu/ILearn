"""P5-deep: structural signature + distillation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.experience.distill_runner import run_distillation
from ilearn.experience.distiller import distill_candidates
from ilearn.experience.models import ExperienceRecord
from ilearn.experience.signature import StructuralSignature, extract_signature
from ilearn.experience.store import ExperienceStore


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def sample_events():
    return [
        {"event_type": "noise.heartbeat", "event_id": "n1"},
        {
            "event_type": "diagnosis.completed",
            "event_id": "d1",
            "confidence_band": "low",
        },
        {"event_type": "tutoring.hint", "event_id": "h1", "hint_level": 1},
        {"event_type": "grade.completed", "event_id": "g1", "score": 0.4},
    ]


@pytest.fixture
def record_factory(now):
    def _make(
        strategy: str = "hint_l1",
        outcome: str = "effective",
        *,
        n: int = 1,
        form: str = "episodic",
        signature: list[str] | None = None,
        skill: str = "frac",
    ):
        sig = signature or ["diagnose:low", "hint:1"]
        return [
            ExperienceRecord(
                record_id=f"{strategy}-{form}-{i}",
                learner_segment={"stage": "k12", "skill": skill},
                situation="hint_before_attempt",
                structural_signature=list(sig),
                strategy=strategy,
                outcome=outcome,  # type: ignore[arg-type]
                form=form,  # type: ignore[arg-type]
                evidence_refs=[f"e-{i}"],
                created_at=now,
                state_version_at_creation=10,
            )
            for i in range(n)
        ]

    return _make


class FakeEventLog:
    def __init__(self) -> None:
        self.rows: list[tuple] = []

    def append(self, event_type: str, payload: dict, learner_id: str) -> str:
        self.rows.append((event_type, payload, learner_id))
        return f"e{len(self.rows)}"


def test_extract_signature_ignores_noise(sample_events):
    sig = extract_signature(sample_events)
    assert all(not t.startswith("noise") for t in sig.tokens)
    assert any(t.startswith("diagnose:") for t in sig.tokens)


def test_structural_prefix_filters_pool(record_factory, now):
    target_sig = StructuralSignature(("diagnose:low", "hint:1"))
    matching = record_factory(
        signature=["diagnose:low", "hint:1", "grade:fail"], n=4
    )
    non_matching = record_factory(signature=["diagnose:high", "hint:3"], n=10)
    prior = ExperienceStore(matching + non_matching).retrieve(
        {"stage": "k12", "skill": "frac"},
        "hint_before_attempt",
        current_state_version=10,
        now=now,
        signature=target_sig,
    )
    assert prior is not None
    assert all(r.structural_signature[0] == "diagnose:low" for r in prior.refs)


def test_distilled_outranks_episodic(record_factory, now):
    episodic = record_factory("hint_l1", "effective", n=3, form="episodic")
    distilled = record_factory("hint_l1", "effective", n=1, form="distilled")
    prior = ExperienceStore(episodic + distilled).retrieve(
        {"stage": "k12", "skill": "frac"},
        "hint_before_attempt",
        current_state_version=10,
        now=now,
    )
    assert prior is not None
    assert prior.confidence > 0


def test_distill_requires_stable_majority(record_factory):
    unstable = record_factory("hint_l2", "effective", n=3) + record_factory(
        "hint_l2", "ineffective", n=3
    )
    assert distill_candidates(unstable, min_episodic=5, stable_ratio=0.7) == []


def test_distill_idempotent(record_factory):
    store = ExperienceStore(record_factory("hint_l1", "effective", n=6))
    log = FakeEventLog()
    first = run_distillation(store, log, "L1")
    second = run_distillation(store, log, "L1")
    assert len(first) == 1 and second == []
    assert any(r[0] == "experience.distilled" for r in log.rows)
    assert log.rows[0][1]["derived_from"]
