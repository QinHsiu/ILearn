"""Active skill registry with invocation feedback / deprecation."""

from __future__ import annotations

from ilearn.skills.models import TeachingSkill


class SkillRegistry:
    def __init__(self, skills: list[TeachingSkill] | None = None) -> None:
        self._skills = {s.skill_id: s for s in skills or []}

    def register(self, skill: TeachingSkill) -> None:
        if not skill.validate_skill():
            raise ValueError(f"invalid skill: {skill.skill_id}")
        skill.status = "active"
        self._skills[skill.skill_id] = skill

    def list_active(self) -> list[TeachingSkill]:
        return [s for s in self._skills.values() if s.status == "active"]

    def lookup(
        self, signature_prefix: list[str], segment: dict
    ) -> TeachingSkill | None:
        candidates = [
            s
            for s in self._skills.values()
            if s.status == "active"
            and list(s.structural_signature[: len(signature_prefix)]) == list(signature_prefix)
            and s.learner_segment.get("skill") == segment.get("skill")
        ]
        return max(candidates, key=lambda s: s.confidence) if candidates else None

    def record_invocation(self, skill_id: str, success: bool) -> None:
        s = self._skills.get(skill_id)
        if s is None:
            return
        s.invocation_count += 1
        if success:
            s.success_count += 1
        if s.invocation_count >= 5 and s.success_count / s.invocation_count < 0.5:
            s.status = "deprecated"
