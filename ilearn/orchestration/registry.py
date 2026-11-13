"""Template registry — select lifecycle FSM by stage + goal affinity."""

from __future__ import annotations

from ilearn.orchestration.k12_template import (
    AdultCompanionTemplate,
    K12MathHostTemplate,
    K12Template,
)
from ilearn.orchestration.template import StateMachineTemplate


class TemplateRegistry:
    def __init__(self, templates: list[StateMachineTemplate] | None = None) -> None:
        items = templates or [
            K12MathHostTemplate(),
            AdultCompanionTemplate(),
            K12Template(),
        ]
        self._templates = {t.template_id: t for t in items}

    def select(self, stage: str, goal_type: str) -> StateMachineTemplate:
        candidates = [
            t for t in self._templates.values() if stage in t.applicable_stages
        ]
        if not candidates:
            raise LookupError(f"no template for stage={stage}")
        return max(
            candidates,
            key=lambda t: float(getattr(t, "goal_affinity", {}).get(goal_type, 0.0)),
        )

    def register(self, template: StateMachineTemplate) -> None:
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> StateMachineTemplate:
        return self._templates[template_id]
