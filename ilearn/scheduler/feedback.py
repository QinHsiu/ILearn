"""Pure-function feedback: DispatchConsumption → LearnerState + TriggerPolicy."""

from __future__ import annotations

from datetime import datetime, timezone

from ilearn.core.learner_state import LearnerState
from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.spaced_repetition import SM2State, next_due, sm2_update
from ilearn.scheduler.trigger_policy import TriggerPolicy


class StateInvariantError(RuntimeError):
    """Raised when consumption would violate version monotonicity."""


def apply_consumption(
    state: LearnerState,
    consumption: DispatchConsumption,
    receipt_state_version: int | None = None,
    policy: TriggerPolicy | None = None,
    *,
    skill_ids: list[str] | None = None,
) -> LearnerState:
    """纯函数：消费结果反馈到状态，并可选更新触发策略。

    关键不变量：消费后的 state.version 必须严格大于回执的 state_version。
    """
    new = state.model_copy(deep=True)
    new.version += 1

    rsv = (
        receipt_state_version
        if receipt_state_version is not None
        else int(consumption.receipt_state_version)
    )
    if new.version <= rsv:
        raise StateInvariantError(
            f"consumption would not advance state: {new.version} <= {rsv}"
        )

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
                "last_reset": False,
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
                "last_reset": True,
                "reset_reason": "dispatch_expired",
            }

    if consumption.outcome == "dismissed":
        prefs = list(new.engagement_signals.get("dismissed_triggers") or [])
        prefs.append(consumption.receipt_id)
        new.engagement_signals["dismissed_triggers"] = prefs

    if policy is not None:
        success = consumption.outcome == "responded" and (consumption.quality or 0) >= 4
        policy.update(consumption.trigger, success)

    new.state_hash = new.compute_hash()
    return new


def _as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
