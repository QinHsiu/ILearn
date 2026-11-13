"""K12 state-machine templates — wrap host FSM; do not rewrite teaching logic."""

from __future__ import annotations

from ilearn.core.schemas import SessionPhase


class K12Template:
    """Canonical six-phase template (uppercase states) for registry / docs / tests."""

    template_id = "k12-standard"
    applicable_stages = {"k12"}
    goal_affinity = {"exam_prep": 0.9, "habit": 0.6}

    _TRANSITIONS = {
        ("ONBOARD", "onboard.completed"): "ASSESS",
        ("ASSESS", "assess.completed"): "PRACTICE",
        ("PRACTICE", "practice.completed"): "GRADE",
        ("GRADE", "grade.completed"): "DIAGNOSE",
        ("DIAGNOSE", "diagnose.completed"): "PLAN",
        ("PLAN", "plan.completed"): "PRACTICE_LOOP",
        ("PRACTICE_LOOP", "loop.completed"): "PLAN",
    }

    def initial_state(self) -> str:
        return "ONBOARD"

    def transitions(self, state: str, event_type: str) -> str | None:
        return self._TRANSITIONS.get((state, event_type))


class K12MathHostTemplate:
    """Wrap existing host SessionPhase transitions — regression-stable."""

    template_id = "k12_math_host"
    applicable_stages = {
        "primary",
        "junior_high",
        "senior_high",
        "early_childhood",
        "k12",
    }
    goal_affinity = {
        "assess_remediate": 1.0,
        "exam_prep": 0.95,
        "companion_chat": 0.6,
        "spaced_review": 0.5,
        "habit": 0.6,
    }

    _edges: dict[tuple[str, str], str] = {
        (SessionPhase.ONBOARD.value, "start_assess"): SessionPhase.ASSESS.value,
        (SessionPhase.ASSESS.value, "submit"): SessionPhase.GRADE.value,
        (SessionPhase.GRADE.value, "diagnose"): SessionPhase.DIAGNOSE.value,
        (SessionPhase.DIAGNOSE.value, "plan"): SessionPhase.PLAN.value,
        (SessionPhase.PLAN.value, "practice"): SessionPhase.PRACTICE_LOOP.value,
        (SessionPhase.PRACTICE_LOOP.value, "idle"): SessionPhase.IDLE.value,
        # Also accept the abstract completed.* events for HostStateMachineBackend.advance
        (SessionPhase.ONBOARD.value, "onboard.completed"): SessionPhase.ASSESS.value,
        (SessionPhase.ASSESS.value, "assess.completed"): SessionPhase.PRACTICE.value,
        (SessionPhase.PRACTICE.value, "practice.completed"): SessionPhase.GRADE.value,
        (SessionPhase.GRADE.value, "grade.completed"): SessionPhase.DIAGNOSE.value,
        (SessionPhase.DIAGNOSE.value, "diagnose.completed"): SessionPhase.PLAN.value,
        (SessionPhase.PLAN.value, "plan.completed"): SessionPhase.PRACTICE_LOOP.value,
        (SessionPhase.PRACTICE_LOOP.value, "loop.completed"): SessionPhase.PLAN.value,
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
