"""IntelliCode-style centralized versioned learner state (single-writer)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now
from ilearn.core.state_event import StateEvent


class MasteryEstimate(BaseModel):
    skill_id: str
    mastery: float = Field(ge=0.0, le=1.0)
    evidence_count: int = 0
    last_updated: datetime = Field(default_factory=utc_now)


class Misconception(BaseModel):
    code: str
    description: str
    first_seen: datetime = Field(default_factory=utc_now)
    occurrence_count: int = 1


class LearnerState(BaseModel):
    """All agent writes project here; sessions read the folded projection."""

    learner_id: str
    version: int = 0
    goals: list[str] = Field(default_factory=list)
    mastery: dict[str, MasteryEstimate] = Field(default_factory=dict)
    misconceptions: list[Misconception] = Field(default_factory=list)
    review_schedule: dict[str, datetime] = Field(default_factory=dict)
    engagement_signals: dict[str, Any] = Field(default_factory=dict)
    state_hash: str = ""

    def compute_hash(self) -> str:
        payload = self.model_dump_json(exclude={"state_hash", "version"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal_initial(self) -> LearnerState:
        sealed = self.model_copy(deep=True)
        sealed.version = 0
        sealed.state_hash = sealed.compute_hash()
        return sealed

    def apply(self, event: StateEvent) -> LearnerState:
        """Single-writer transition: one event type → one pure handler."""
        if event.prev_state_hash and event.prev_state_hash != self.state_hash:
            raise ValueError(
                f"hash chain broken at {event.event_id}: "
                f"expected prev={self.state_hash}, got={event.prev_state_hash}"
            )
        new = self.model_copy(deep=True)
        new.version += 1
        handler = _EVENT_HANDLERS.get(event.event_type)
        if handler is None:
            raise ValueError(f"unknown event_type: {event.event_type}")
        # Inject event time so replays are deterministic (no utc_now() drift).
        payload = dict(event.payload)
        payload.setdefault("timestamp", event.occurred_at)
        payload.setdefault("first_seen", event.occurred_at)
        handler(new, payload)
        new.state_hash = new.compute_hash()
        return new


def _parse_ts(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return utc_now()


def _on_mastery_update(state: LearnerState, payload: dict) -> None:
    skill_id = str(payload["skill_id"])
    prev = state.mastery.get(skill_id)
    mastery = float(payload["mastery"])
    mastery = max(0.0, min(1.0, mastery))
    state.mastery[skill_id] = MasteryEstimate(
        skill_id=skill_id,
        mastery=mastery,
        evidence_count=(prev.evidence_count if prev else 0) + int(payload.get("delta_evidence", 1)),
        last_updated=_parse_ts(payload.get("timestamp")),
    )


def _on_misconception(state: LearnerState, payload: dict) -> None:
    code = str(payload["code"])
    for m in state.misconceptions:
        if m.code == code:
            m.occurrence_count += 1
            return
    state.misconceptions.append(
        Misconception(
            code=code,
            description=str(payload.get("description") or code),
            first_seen=_parse_ts(payload.get("first_seen") or payload.get("timestamp")),
            occurrence_count=int(payload.get("occurrence_count", 1)),
        )
    )


def _on_review_scheduled(state: LearnerState, payload: dict) -> None:
    skill_id = str(payload["skill_id"])
    state.review_schedule[skill_id] = _parse_ts(payload["due_at"])


def _on_engagement_updated(state: LearnerState, payload: dict) -> None:
    state.engagement_signals.update(dict(payload))


def _on_goal_set(state: LearnerState, payload: dict) -> None:
    goals = payload.get("goals")
    if isinstance(goals, list):
        state.goals = [str(g) for g in goals]
    elif payload.get("goal"):
        goal = str(payload["goal"])
        if goal not in state.goals:
            state.goals.append(goal)


_EVENT_HANDLERS: dict[str, Callable[[LearnerState, dict], None]] = {
    "mastery.update": _on_mastery_update,
    "misconception.detected": _on_misconception,
    "review.scheduled": _on_review_scheduled,
    "engagement.updated": _on_engagement_updated,
    "goal.set": _on_goal_set,
}


def register_event_handler(
    event_type: str, handler: Callable[[LearnerState, dict], None]
) -> None:
    """Plugin hook for lifecycle templates (P3) without editing core handlers."""
    _EVENT_HANDLERS[event_type] = handler
