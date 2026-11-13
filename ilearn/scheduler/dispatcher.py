"""Scheduler consumes LearnerState; emits receipts + review.scheduled events."""

from __future__ import annotations

from datetime import datetime, timezone

from ilearn.core.learner_state import LearnerState
from ilearn.core.state_event import StateEvent
from ilearn.scheduler.receipt import ProactiveDispatchReceipt
from ilearn.scheduler.spaced_repetition import (
    SM2State,
    due_at,
    quality_from_mastery,
    sm2_update,
)


def build_review_events_from_mastery(
    state: LearnerState,
    *,
    now: datetime | None = None,
) -> list[StateEvent]:
    """For each skill, schedule next review via SM-2 using current mastery."""
    now = now or datetime.now(timezone.utc)
    events: list[StateEvent] = []
    for skill_id, est in state.mastery.items():
        sm2 = SM2State()
        # Warm from evidence_count as prior reviews (capped).
        for _ in range(min(est.evidence_count, 3)):
            sm2 = sm2_update(sm2, quality_from_mastery(est.mastery))
        due = due_at(sm2, now=now)
        events.append(
            StateEvent(
                learner_id=state.learner_id,
                event_type="review.scheduled",
                payload={
                    "skill_id": skill_id,
                    "due_at": due.isoformat(),
                    "interval_days": sm2.interval_days,
                    "ease_factor": sm2.ease_factor,
                },
            )
        )
    return events


def due_dispatches(
    state: LearnerState,
    *,
    now: datetime | None = None,
) -> list[ProactiveDispatchReceipt]:
    """Produce proactive receipts for skills whose review window is due."""
    now = now or datetime.now(timezone.utc)
    receipts: list[ProactiveDispatchReceipt] = []
    for skill_id, due in state.review_schedule.items():
        due_aware = due if due.tzinfo else due.replace(tzinfo=timezone.utc)
        if due_aware <= now:
            receipts.append(
                ProactiveDispatchReceipt(
                    learner_id=state.learner_id,
                    trigger="spaced_repetition",
                    reason=f"该知识点 SM-2 间隔已到：{skill_id}",
                    evidence_refs=[f"skill:{skill_id}", f"state_v{state.version}"],
                    state_version=state.version,
                    skill_id=skill_id,
                ).seal()
            )
    # Engagement drop heuristic
    loops = int(state.engagement_signals.get("loop_count") or 0)
    frustration = float(state.engagement_signals.get("frustration") or 0.0)
    if loops >= 2 and frustration >= 0.6:
        receipts.append(
            ProactiveDispatchReceipt(
                learner_id=state.learner_id,
                trigger="engagement_drop",
                reason="巩固轮次升高且挫败信号偏高，建议主动短干预",
                evidence_refs=[f"state_v{state.version}", "engagement.updated"],
                state_version=state.version,
            ).seal()
        )
    return receipts
