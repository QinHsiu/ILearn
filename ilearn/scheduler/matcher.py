"""Match learner.* events to pending ProactiveDispatchReceipts (auditable)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.models import ProactiveDispatchReceipt

CONSUMPTION_WINDOW = timedelta(hours=48)

_MATCHABLE = frozenset(
    {"practice.completed", "learner.dismissed", "practice.abandoned"}
)


def _as_aware(dt: datetime | str) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ConsumptionMatcher:
    """将 learner.* 事件与未消费的 dispatch 回执匹配。

    规则：时间在窗口内 + 知识点有交集（或回执未限定技能）+ 练习完成 / dismiss / abandon。
    """

    def __init__(self, pending_receipts: list[ProactiveDispatchReceipt]) -> None:
        self._pending = {r.receipt_id: r for r in pending_receipts}

    def match(self, event: dict[str, Any]) -> DispatchConsumption | None:
        etype = event.get("event_type", "")
        if etype not in _MATCHABLE:
            return None
        occurred_at = _as_aware(event["occurred_at"])
        skill_id = event.get("skill_id")

        for receipt in list(self._pending.values()):
            scheduled = _as_aware(receipt.scheduled_at)
            delta = occurred_at - scheduled
            if delta < timedelta(0) or delta > CONSUMPTION_WINDOW:
                continue
            skill_ids = list(receipt.skill_ids)
            if receipt.skill_id and receipt.skill_id not in skill_ids:
                skill_ids.append(receipt.skill_id)
            if skill_ids and skill_id and skill_id not in skill_ids:
                continue
            if etype == "learner.dismissed":
                cons = self._make(receipt, event, "dismissed", quality=None, skill_ids=skill_ids)
            elif etype == "practice.abandoned":
                cons = self._make(receipt, event, "expired", quality=None, skill_ids=skill_ids)
            else:
                quality = self._quality_from_event(event)
                cons = self._make(receipt, event, "responded", quality=quality, skill_ids=skill_ids)
            # Remove from pending so one receipt is consumed once
            self._pending.pop(receipt.receipt_id, None)
            return cons
        return None

    def expire_overdue(
        self, now: datetime | None = None, *, evidence_event_id: str | None = None
    ) -> list[DispatchConsumption]:
        """Emit expired consumptions for receipts past the window (observable, not silent)."""
        now = _as_aware(now or datetime.now(timezone.utc))
        expired: list[DispatchConsumption] = []
        for receipt_id, receipt in list(self._pending.items()):
            scheduled = _as_aware(receipt.scheduled_at)
            if now - scheduled <= CONSUMPTION_WINDOW:
                continue
            skill_ids = list(receipt.skill_ids)
            if receipt.skill_id and receipt.skill_id not in skill_ids:
                skill_ids.append(receipt.skill_id)
            refs = [evidence_event_id] if evidence_event_id else [f"expire:{receipt_id}"]
            cons = DispatchConsumption(
                consumption_id=f"cons-{uuid4().hex[:12]}",
                receipt_id=receipt.receipt_id,
                learner_id=receipt.learner_id,
                outcome="expired",
                quality=None,
                consumed_at=now,
                evidence_refs=refs,
                skill_ids=skill_ids,
            ).seal()
            expired.append(cons)
            self._pending.pop(receipt_id, None)
        return expired

    @staticmethod
    def _quality_from_event(event: dict[str, Any]) -> int:
        acc = float(event.get("accuracy") or 0.0)
        if acc >= 0.9:
            return 5
        if acc >= 0.75:
            return 4
        if acc >= 0.6:
            return 3
        if acc >= 0.4:
            return 2
        return 1

    @staticmethod
    def _make(
        receipt: ProactiveDispatchReceipt,
        event: dict[str, Any],
        outcome: str,
        quality: int | None,
        skill_ids: list[str],
    ) -> DispatchConsumption:
        eid = str(event.get("event_id") or "")
        return DispatchConsumption(
            consumption_id=f"cons-{uuid4().hex[:12]}",
            receipt_id=receipt.receipt_id,
            learner_id=receipt.learner_id,
            outcome=outcome,  # type: ignore[arg-type]
            quality=quality,
            consumed_at=_as_aware(event["occurred_at"]),
            evidence_refs=[eid] if eid else [],
            skill_ids=skill_ids,
        ).seal()
