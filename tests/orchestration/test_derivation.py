"""P6-deep: derivation layer + trace replay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.orchestration.derivation import derive_mastery
from ilearn.orchestration.migration import DerivationSpec, SkillMapping, StateMigrationContract
from ilearn.orchestration.migration_replay import replay_migration
from ilearn.orchestration.migrator import StateMigrator


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def state_factory(now):
    def _make(**kwargs) -> LearnerState:
        mastery_raw = kwargs.pop("mastery", {})
        mastery = {}
        for sid, val in mastery_raw.items():
            if isinstance(val, MasteryEstimate):
                mastery[sid] = val
            else:
                mastery[sid] = MasteryEstimate(
                    skill_id=sid,
                    mastery=float(val),
                    evidence_count=5,
                    last_updated=now,
                )
        state = LearnerState(
            learner_id=kwargs.pop("learner_id", "L1"),
            mastery=mastery,
            **kwargs,
        )
        return state.seal_initial()

    return _make


@pytest.fixture
def contract_factory():
    def _make(
        mappings: list[dict] | None = None,
        *,
        derivations: list[dict] | None = None,
        default_target_skill: str | None = None,
    ) -> StateMigrationContract:
        return StateMigrationContract(
            contract_id="ctr-d",
            source_template_id="k12-standard",
            target_template_id="adult_companion",
            skill_mappings=[SkillMapping(**m) for m in (mappings or [])],
            derivations=[DerivationSpec(**d) for d in (derivations or [])],
            default_target_skill=default_target_skill,
        )

    return _make


def test_evidence_decay_mean_prefers_recent(state_factory, now):
    old = MasteryEstimate(
        skill_id="a",
        mastery=0.9,
        evidence_count=5,
        last_updated=now - timedelta(days=365),
    )
    recent = MasteryEstimate(
        skill_id="b", mastery=0.4, evidence_count=5, last_updated=now
    )
    state = state_factory(mastery={"a": old, "b": recent})
    spec = DerivationSpec(
        target_skill="stat.basics",
        rule="evidence_decay_mean",
        source_skills=["a", "b"],
        half_life_days=90,
    )
    value, trace = derive_mastery(state, spec, now)
    assert value < 0.6
    assert trace["rule"] == "evidence_decay_mean"


def test_small_evidence_shrinks_toward_neutral(state_factory, now):
    one = MasteryEstimate(
        skill_id="a", mastery=1.0, evidence_count=1, last_updated=now
    )
    state = state_factory(mastery={"a": one})
    spec = DerivationSpec(
        target_skill="t", rule="evidence_max", source_skills=["a"]
    )
    value, trace = derive_mastery(state, spec, now)
    assert value < 0.6
    assert trace["shrink_factor"] < 0.2


def test_derivation_trace_replay_stable(state_factory, contract_factory, now):
    state = state_factory(mastery={"frac.add": 0.8})
    contract = contract_factory(
        derivations=[
            {
                "target_skill": "algebra.frac",
                "rule": "evidence_mean",
                "source_skills": ["frac.add"],
            }
        ]
    )
    _, receipt = StateMigrator().migrate(state, contract, now)
    assert receipt.derivation_traces
    assert replay_migration(state, receipt, contract)


def test_orphaned_not_consumed_by_derivation(state_factory, contract_factory, now):
    state = state_factory(mastery={"frac.add": 0.8, "weird.skill": 0.5})
    contract = contract_factory(
        derivations=[
            {
                "target_skill": "algebra.frac",
                "rule": "evidence_mean",
                "source_skills": ["frac.add"],
            }
        ]
    )
    _, receipt = StateMigrator().migrate(state, contract, now)
    assert "weird.skill" in receipt.orphaned_skills
