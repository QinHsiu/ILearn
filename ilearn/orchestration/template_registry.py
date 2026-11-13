"""Lifecycle state-machine template registry (P3). K12 wraps host FSM."""

from __future__ import annotations

from typing import Protocol

from ilearn.core.schemas import SessionPhase


class StateMachineTemplate(Protocol):
    template_id: str
    applicable_stages: set[str]
    goal_affinity: dict[str, float]

    def initial_state(self) -> str: ...

    def transitions(self, state: str, event_type: str) -> str | None: ...


class K12MathHostTemplate:
    """Wrap existing six-phase host state machine — no rewrite."""

    template_id = "k12_math_host"
    applicable_stages = {
        "primary",
        "junior_high",
        "senior_high",
        "early_childhood",
    }
    goal_affinity = {
        "assess_remediate": 1.0,
        "companion_chat": 0.6,
        "spaced_review": 0.5,
    }

    _edges: dict[tuple[str, str], str] = {
        (SessionPhase.ONBOARD.value, "start_assess"): SessionPhase.ASSESS.value,
        (SessionPhase.ASSESS.value, "submit"): SessionPhase.GRADE.value,
        (SessionPhase.GRADE.value, "diagnose"): SessionPhase.DIAGNOSE.value,
        (SessionPhase.DIAGNOSE.value, "plan"): SessionPhase.PLAN.value,
        (SessionPhase.PLAN.value, "practice"): SessionPhase.PRACTICE_LOOP.value,
        (SessionPhase.PRACTICE_LOOP.value, "idle"): SessionPhase.IDLE.value,
    }

    def initial_state(self) -> str:
        return SessionPhase.ONBOARD.value

    def transitions(self, state: str, event_type: str) -> str | None:
        return self._edges.get((state, event_type))


class AdultCompanionTemplate:
    """Thin companion-first template for career / midlife / elder / HE."""

    template_id = "adult_companion"
    applicable_stages = {"undergrad", "graduate", "career", "midlife", "elder"}
    goal_affinity = {
        "companion_chat": 1.0,
        "spaced_review": 0.8,
        "assess_remediate": 0.3,
    }

    def initial_state(self) -> str:
        return "companion"

    def transitions(self, state: str, event_type: str) -> str | None:
        edges = {
            ("companion", "evaluate"): "assess",
            ("assess", "plan"): "week_plan",
            ("week_plan", "idle"): "companion",
            ("companion", "review_due"): "spaced_review",
            ("spaced_review", "done"): "companion",
        }
        return edges.get((state, event_type))


class TemplateRegistry:
    def __init__(self, templates: list[StateMachineTemplate] | None = None) -> None:
        items = templates or [K12MathHostTemplate(), AdultCompanionTemplate()]
        self._templates = {t.template_id: t for t in items}

    def select(self, learner_stage: str, goal_type: str) -> StateMachineTemplate:
        candidates = [
            t
            for t in self._templates.values()
            if learner_stage in t.applicable_stages
        ]
        if not candidates:
            raise LookupError(f"no template for stage={learner_stage}")
        return max(
            candidates,
            key=lambda t: float(getattr(t, "goal_affinity", {}).get(goal_type, 0.0)),
        )

    def get(self, template_id: str) -> StateMachineTemplate:
        return self._templates[template_id]
