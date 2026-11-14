"""Induce TeachingSkill from episodic ExperienceRecords (rule-based)."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from ilearn.experience.models import ExperienceRecord
from ilearn.skills.models import SkillParameter, TeachingSkill


def induce_skills(
    records: list[ExperienceRecord],
    *,
    min_episodic: int = 5,
    stability: float = 0.75,
) -> list[TeachingSkill]:
    """从 episodic 记录归纳可执行技能。仅 effective 记录作为分子。"""
    groups: dict[tuple, list[ExperienceRecord]] = defaultdict(list)
    for r in records:
        if r.form != "episodic" or r.outcome != "effective":
            continue
        key = (
            tuple(r.structural_signature[:2]),
            r.learner_segment.get("skill"),
            r.learner_segment.get("stage"),
        )
        groups[key].append(r)

    skills: list[TeachingSkill] = []
    for (sig_prefix, skill, stage), group in groups.items():
        if len(group) < min_episodic:
            continue
        total = sum(
            1
            for r in records
            if tuple(r.structural_signature[:2]) == sig_prefix
            and r.learner_segment.get("skill") == skill
            and r.learner_segment.get("stage") == stage
            and r.form == "episodic"
        )
        if len(group) / max(1, total) < stability:
            continue
        dominant = Counter(r.strategy for r in group).most_common(1)[0][0]
        action = _strategy_to_action(dominant)
        if action is None:
            continue
        created = max((_as_dt(r.created_at) for r in group), default=None)
        token0 = sig_prefix[0].split(":")[0] if sig_prefix else "sig"
        skills.append(
            TeachingSkill(
                skill_id=f"sk-{skill}-{stage}-{token0}",
                structural_signature=list(sig_prefix),
                derived_from_episodic=[r.record_id for r in group],
                parameters=[
                    SkillParameter(
                        name="hint_level",
                        kind="hint_level",
                        default=action.get("hint_level"),
                    )
                ],
                action_sequence=[action],
                learner_segment=dict(group[0].learner_segment),
                confidence=round(len(group) / max(1, total), 3),
                created_at=created or group[0].created_at,
                state_version_at_creation=max(
                    int(r.state_version_at_creation) for r in group
                ),
            )
        )
    return skills


def _strategy_to_action(strategy: str) -> dict | None:
    if strategy.startswith("hint_level_"):
        return {"action": "hint", "hint_level": int(strategy.rsplit("_", 1)[-1])}
    if strategy.startswith("hint_l") and strategy[6:].isdigit():
        return {"action": "hint", "hint_level": int(strategy[6:])}
    if strategy == "no_hint":
        return {"action": "prompt_only"}
    return None


def _as_dt(value: datetime | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
