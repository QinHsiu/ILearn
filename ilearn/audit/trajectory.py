"""Lifelong trajectory reconstruction from append-only event logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

_TRAJECTORY_EVENT_TYPES = {
    "mastery.update",
    "misconception.detected",
    "scheduler.dispatch",
    "scheduler.consumed",
    "experience.distilled",
    "learner.state_migrated",
    "safety.reviewed",
    "orchestration.unexpected",
}


class TrajectoryNode(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    state_version_before: int = -1
    state_version_after: int = -1
    state_hash_before: str = ""
    state_hash_after: str = ""
    summary: str = ""


class Trajectory(BaseModel):
    learner_id: str
    window_start: datetime
    window_end: datetime
    nodes: list[TrajectoryNode] = Field(default_factory=list)
    start_state_hash: str = ""
    end_state_hash: str = ""
    is_contiguous: bool = True


def _as_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def build_trajectory(
    events: list[dict],
    learner_id: str,
    window: tuple[datetime, datetime] | None = None,
) -> Trajectory:
    lo = window[0] if window else datetime.min.replace(tzinfo=timezone.utc)
    hi = window[1] if window else datetime.max.replace(tzinfo=timezone.utc)
    if lo.tzinfo is None:
        lo = lo.replace(tzinfo=timezone.utc)
    if hi.tzinfo is None:
        hi = hi.replace(tzinfo=timezone.utc)

    filtered: list[dict] = []
    for e in events:
        if str(e.get("learner_id") or "") != learner_id:
            continue
        if e.get("event_type") not in _TRAJECTORY_EVENT_TYPES:
            continue
        occurred = _as_dt(e.get("occurred_at")) or lo
        if occurred < lo or occurred > hi:
            continue
        filtered.append(e)
    filtered.sort(key=lambda e: _as_dt(e.get("occurred_at")) or lo)

    nodes: list[TrajectoryNode] = []
    for ev in filtered:
        before = str(ev.get("prev_state_hash") or "")
        after = str(ev.get("state_hash") or "")
        nodes.append(
            TrajectoryNode(
                event_id=str(ev.get("event_id") or ""),
                event_type=str(ev.get("event_type") or ""),
                occurred_at=_as_dt(ev.get("occurred_at")) or lo,
                state_version_before=int(ev.get("state_version_before", -1)),
                state_version_after=int(ev.get("state_version_after", -1)),
                state_hash_before=before,
                state_hash_after=after,
                summary=_summarize(ev),
            )
        )

    contiguous = True
    expected: str | None = None
    for node in nodes:
        if expected is not None and node.state_hash_before != expected:
            contiguous = False
            break
        expected = node.state_hash_after

    return Trajectory(
        learner_id=learner_id,
        window_start=lo,
        window_end=hi,
        nodes=nodes,
        start_state_hash=nodes[0].state_hash_before if nodes else "",
        end_state_hash=nodes[-1].state_hash_after if nodes else "",
        is_contiguous=contiguous,
    )


def _summarize(ev: dict) -> str:
    p = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
    merged = {**p, **{k: v for k, v in ev.items() if k != "payload"}}
    t = str(ev.get("event_type") or "")
    if t == "mastery.update":
        return f"{merged.get('skill_id')} → {merged.get('mastery')}"
    if t == "scheduler.dispatch":
        return f"{merged.get('trigger')}: {str(merged.get('reason', ''))[:40]}"
    if t == "scheduler.consumed":
        return f"{merged.get('trigger')} → {merged.get('outcome')}"
    if t == "experience.distilled":
        return f"distilled {merged.get('record_id')}"
    if t == "learner.state_migrated":
        return (
            f"migrated v{merged.get('source_version')}→v{merged.get('target_version')}"
        )
    if t == "safety.reviewed":
        rules = merged.get("rule_ids") or []
        return f"{merged.get('decision')}: {','.join(rules)}"
    return t
