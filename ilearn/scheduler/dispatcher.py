"""Bypass Scheduler — produces receipts only; never calls LLM or session FSM."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol

from ilearn.core.learner_state import LearnerState
from ilearn.core.state_event import StateEvent
from ilearn.scheduler.models import ProactiveDispatchReceipt, ReviewItem
from ilearn.scheduler.spaced_repetition import (
    SM2State,
    next_due,
    quality_from_mastery,
    sm2_update,
)


class EventLogWriter(Protocol):
    def append(self, event_type: str, payload: dict, learner_id: str) -> str: ...


class _NullEventLog:
    def append(self, event_type: str, payload: dict, learner_id: str) -> str:
        return ""


class Scheduler:
    """旁路调度器：不进入会话状态机；只产生回执与待推送任务。"""

    def __init__(
        self,
        event_log: EventLogWriter | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._log = event_log or _NullEventLog()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def scan(self, state: LearnerState) -> list[ProactiveDispatchReceipt]:
        now = self._clock()
        receipts: list[ProactiveDispatchReceipt] = []

        due_items = self._due_review_items(state, now)
        if due_items:
            receipts.append(
                self._make_receipt(
                    state=state,
                    trigger="spaced_repetition",
                    reason=f"{len(due_items)} 个知识点的复习间隔已到",
                    skill_ids=[item.skill_id for item in due_items],
                )
            )

        engagement = state.engagement_signals or {}
        inactive = int(engagement.get("consecutive_inactive_days") or 0)
        loops = int(engagement.get("loop_count") or 0)
        frustration = float(engagement.get("frustration") or 0.0)
        if inactive >= 3 or (loops >= 2 and frustration >= 0.6):
            skill_ids = list(state.mastery.keys())[-3:]
            reason = (
                f"连续 {inactive} 天无学习活动"
                if inactive >= 3
                else "巩固轮次升高且挫败信号偏高，建议主动短干预"
            )
            receipts.append(
                self._make_receipt(
                    state=state,
                    trigger="engagement_drop",
                    reason=reason,
                    skill_ids=skill_ids,
                )
            )

        deviation = float(engagement.get("goal_deviation_ratio") or 0.0)
        if deviation > 0.3:
            receipts.append(
                self._make_receipt(
                    state=state,
                    trigger="goal_deviation",
                    reason=f"当前进度偏离目标 {deviation:.0%}",
                    skill_ids=[],
                )
            )

        for receipt in receipts:
            self._log.append(
                "scheduler.dispatch",
                receipt.model_dump(mode="json"),
                state.learner_id,
            )
        return receipts

    def _due_review_items(self, state: LearnerState, now: datetime) -> list[ReviewItem]:
        items: list[ReviewItem] = []
        for skill_id, due_at in state.review_schedule.items():
            due_aware = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
            if due_aware > now:
                continue
            meta = dict(state.review_meta.get(skill_id) or {})
            items.append(
                ReviewItem(
                    skill_id=skill_id,
                    due_at=due_aware,
                    interval_days=float(meta.get("interval_days", 1.0)),
                    ease_factor=float(meta.get("ease_factor", 2.5)),
                    review_count=int(meta.get("review_count", 0)),
                    last_quality=(
                        int(meta["last_quality"])
                        if meta.get("last_quality") is not None
                        else None
                    ),
                )
            )
        return items

    def _make_receipt(
        self,
        *,
        state: LearnerState,
        trigger: str,
        reason: str,
        skill_ids: list[str],
    ) -> ProactiveDispatchReceipt:
        receipt = ProactiveDispatchReceipt(
            learner_id=state.learner_id,
            trigger=trigger,  # type: ignore[arg-type]
            reason=reason,
            skill_ids=skill_ids,
            skill_id=skill_ids[0] if skill_ids else None,
            evidence_refs=self._collect_evidence_refs(state, skill_ids),
            state_version=state.version,
            state_hash=state.state_hash,
            scheduled_at=self._clock(),
        )
        return receipt.seal()

    @staticmethod
    def _collect_evidence_refs(state: LearnerState, skill_ids: list[str]) -> list[str]:
        refs: list[str] = [f"state_v{state.version}", f"hash:{state.state_hash[:16]}"]
        for skill_id in skill_ids:
            estimate = state.mastery.get(skill_id)
            if estimate:
                refs.append(
                    f"mastery:{skill_id}@{estimate.last_updated.isoformat()}"
                )
            else:
                refs.append(f"skill:{skill_id}")
        return refs


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
        quality = quality_from_mastery(est.mastery)
        for _ in range(min(est.evidence_count, 3)):
            sm2 = sm2_update(sm2, quality)
        due = next_due(sm2, now=now)
        events.append(
            StateEvent(
                learner_id=state.learner_id,
                event_type="review.scheduled",
                payload={
                    "skill_id": skill_id,
                    "due_at": due.isoformat(),
                    "interval_days": sm2.interval_days,
                    "ease_factor": sm2.ease_factor,
                    "review_count": sm2.review_count,
                    "last_quality": quality,
                },
            )
        )
    return events


def due_dispatches(
    state: LearnerState,
    *,
    now: datetime | None = None,
) -> list[ProactiveDispatchReceipt]:
    """Compatibility wrapper — scan without persisting to event log."""
    clock = (lambda: now) if now is not None else None
    return Scheduler(event_log=_NullEventLog(), clock=clock).scan(state)
