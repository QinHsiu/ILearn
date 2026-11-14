"""P9: skill induction / registry / invocation reflux."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ilearn.experience.models import ExperienceRecord
from ilearn.skills.inducer import induce_skills
from ilearn.skills.invocation import invocation_to_episodic
from ilearn.skills.registry import SkillRegistry


@pytest.fixture
def now():
    return datetime(2026, 11, 13, tzinfo=timezone.utc)


@pytest.fixture
def record_factory(now):
    def _make(
        strategy: str,
        outcome: str,
        *,
        n: int = 1,
        signature: list[str] | None = None,
    ):
        sig = signature or ["diagnose:low", "hint:1"]
        return [
            ExperienceRecord(
                record_id=f"{strategy}-{outcome}-{i}",
                learner_segment={"stage": "k12", "skill": "frac"},
                situation="hint_before_attempt",
                structural_signature=list(sig),
                strategy=strategy,
                outcome=outcome,  # type: ignore[arg-type]
                form="episodic",
                evidence_refs=[f"e-{i}"],
                created_at=now,
                state_version_at_creation=1,
            )
            for i in range(n)
        ]

    return _make


def test_induce_requires_stable_dominant(record_factory):
    stable = record_factory(
        "hint_level_2",
        "effective",
        signature=["diagnose:low", "hint:1"],
        n=6,
    )
    assert len(induce_skills(stable, min_episodic=5, stability=0.75)) == 1


def test_induce_rejects_mixed_outcomes(record_factory):
    mixed = record_factory("hint_level_2", "effective", n=3) + record_factory(
        "hint_level_2", "ineffective", n=3
    )
    assert induce_skills(mixed, min_episodic=5, stability=0.75) == []


def test_registry_deprecates_on_low_success(record_factory):
    skill = induce_skills(record_factory("hint_level_2", "effective", n=6))[0]
    reg = SkillRegistry([skill])
    reg.register(skill)
    for _ in range(6):
        reg.record_invocation(skill.skill_id, success=False)
    assert reg._skills[skill.skill_id].status == "deprecated"


def test_invocation_returns_episodic_record(record_factory):
    skill = induce_skills(record_factory("hint_level_2", "effective", n=6))[0]
    rec = invocation_to_episodic(
        skill, "effective", {"skill": "frac"}, ["e1", "e2"], state_version=10
    )
    assert rec.form == "episodic" and skill.skill_id in rec.derived_from
