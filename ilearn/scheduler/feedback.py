"""Pure-function feedback: DispatchConsumption → LearnerState review updates."""

from __future__ import annotations

from datetime import datetime, timezone

from ilearn.core.learner_state import LearnerState
from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.spaced_repetition import SM2State, next_due, sm2_update


def apply_consumption(
    state: LearnerState,
    consumption: DispatchConsumption,
    *,
    skill_ids: list[str] | None = None,
) -> LearnerState:
    """纯函数：消费结果反馈到状态。

    - responded + quality → SM-2 更新 due_at / review_meta
    - expired → 重置间隔并立即重新到期
    - dismissed → 不改调度，只记录偏好信号
    """
    new = state.model_copy(deep=True)
    new.version += 1
    sids = list(skill_ids if skill_ids is not None else consumption.skill_ids)

    if consumption.outcome == "responded" and consumption.quality is not None:
        for sid in sids:
            meta = dict(new.review_meta.get(sid) or {})
            sm2 = SM2State(
                review_count=int(meta.get("review_count", 0)),
                ease_factor=float(meta.get("ease_factor", 2.5)),
                interval_days=float(meta.get("interval_days", 1.0)),
            )
            nxt = sm2_update(sm2, int(consumption.quality))
            due = next_due(nxt, now=_as_aware(consumption.consumed_at))
            new.review_schedule[sid] = due
            new.review_meta[sid] = {
                "interval_days": nxt.interval_days,
                "ease_factor": nxt.ease_factor,
                "review_count": nxt.review_count,
                "last_quality": int(consumption.quality),
            }

    elif consumption.outcome == "expired":
        for sid in sids:
            meta = dict(new.review_meta.get(sid) or {})
            due = _as_aware(consumption.consumed_at)
            new.review_schedule[sid] = due
            new.review_meta[sid] = {
                **meta,
                "due_at": due.isoformat(),
                "review_count": 0,
                "interval_days": 1.0,
                "ease_factor": float(meta.get("ease_factor", 2.5)),
            }

    if consumption.outcome == "dismissed":
        prefs = list(new.engagement_signals.get("dismissed_triggers") or [])
        prefs.append(consumption.receipt_id)
        new.engagement_signals["dismissed_triggers"] = prefs

    new.state_hash = new.compute_hash()
    return new


def _as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
