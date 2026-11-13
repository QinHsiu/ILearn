"""Skill invocation → episodic experience reflux (MemCryst bidirectional loop)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ilearn.experience.models import ExperienceRecord
from ilearn.skills.models import TeachingSkill


def invocation_to_episodic(
    skill: TeachingSkill,
    outcome: str,
    learner_segment: dict,
    event_refs: list[str],
    state_version: int,
) -> ExperienceRecord:
    """技能调用 → 新的 episodic 记录，回流经验库。"""
    action = skill.action_sequence[0] if skill.action_sequence else {}
    strategy = (
        f"hint_level_{action['hint_level']}"
        if action.get("action") == "hint" and "hint_level" in action
        else str(action.get("action") or "skill_invocation")
    )
    return ExperienceRecord(
        record_id=f"inv-{skill.skill_id}-{uuid4().hex[:8]}",
        learner_segment=dict(learner_segment),
        situation=skill.skill_id,
        structural_signature=list(skill.structural_signature),
        strategy=strategy,
        outcome=outcome,  # type: ignore[arg-type]
        form="episodic",
        evidence_refs=list(event_refs),
        created_at=datetime.now(timezone.utc),
        state_version_at_creation=state_version,
        derived_from=[skill.skill_id],
    )
