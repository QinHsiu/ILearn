"""P6: cross-template LearnerState migration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.orchestration.migration import SkillMapping, StateMigrationContract
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
            if isinstance(val, (int, float)):
                mastery[sid] = MasteryEstimate(
                    skill_id=sid, mastery=float(val), evidence_count=1, last_updated=now
                )
            else:
                mastery[sid] = val
        review_raw = kwargs.pop("review_schedule", {})
        schedule = {}
        meta = {}
        for sid, val in review_raw.items():
            if isinstance(val, dict):
                schedule[sid] = val.get("due_at", now)
                meta[sid] = {
                    k: v for k, v in val.items() if k != "due_at"
                }
            else:
                schedule[sid] = val
        state = LearnerState(
            learner_id=kwargs.pop("learner_id", "learner-1"),
            mastery=mastery,
            review_schedule=schedule,
            review_meta=meta,
            **kwargs,
        )
        return state.seal_initial()

    return _make


@pytest.fixture
def contract_factory():
    def _make(
        mappings: list[dict],
        *,
        default_target_skill: str | None = None,
        source_template_id: str = "k12-standard",
        target_template_id: str = "adult_companion",
    ) -> StateMigrationContract:
        return StateMigrationContract(
            contract_id="ctr-test",
            source_template_id=source_template_id,
            target_template_id=target_template_id,
            skill_mappings=[SkillMapping(**m) for m in mappings],
            default_target_skill=default_target_skill,
        )

    return _make


def test_migrate_maps_skills_and_preserves_due_dates(state_factory, contract_factory, now):
    state = state_factory(
        mastery={"frac.add": 0.8, "frac.mul": 0.6},
        review_schedule={"frac.add": {"due_at": now, "interval_days": 5}},
    )
    contract = contract_factory(
        [
            {
                "source_skill": "frac.add",
                "target_skill": "algebra.fraction_add",
                "confidence": 0.9,
            },
            {
                "source_skill": "frac.mul",
                "target_skill": "algebra.fraction_mul",
                "confidence": 1.0,
            },
        ]
    )
    source_hash = state.state_hash
    target, receipt = StateMigrator().migrate(state, contract, now)
    assert state.state_hash == source_hash  # 派生而非覆盖
    assert target.mastery["algebra.fraction_add"].mastery == 0.72
    assert target.review_schedule["algebra.fraction_add"] == now
    assert receipt.orphaned_skills == []
    assert receipt.mapped_skills["frac.add"] == "algebra.fraction_add"


def test_unmapped_skill_becomes_orphaned_without_default(
    state_factory, contract_factory, now
):
    state = state_factory(mastery={"obscure.skill": 0.5})
    contract = contract_factory([], default_target_skill=None)
    target, receipt = StateMigrator().migrate(state, contract, now)
    assert "obscure.skill" in receipt.orphaned_skills
    assert "obscure.skill" in target.engagement_signals["orphaned_skills"]


def test_replay_migration_detects_contract_drift(state_factory, contract_factory, now):
    state = state_factory(mastery={"frac.add": 0.8})
    contract = contract_factory(
        [{"source_skill": "frac.add", "target_skill": "a", "confidence": 1.0}]
    )
    _, receipt = StateMigrator().migrate(state, contract, now)
    contract.skill_mappings[0].target_skill = "b"  # 篡改契约
    with pytest.raises(ValueError, match="contract changed"):
        replay_migration(state, receipt, contract)


def test_replay_migration_pass(state_factory, contract_factory, now):
    state = state_factory(mastery={"frac.add": 0.8})
    contract = contract_factory(
        [{"source_skill": "frac.add", "target_skill": "a", "confidence": 1.0}]
    )
    _, receipt = StateMigrator().migrate(state, contract, now)
    assert replay_migration(state, receipt, contract) is True
