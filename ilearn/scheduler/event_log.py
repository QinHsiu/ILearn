"""Bypass event log for scheduler.dispatch — separate from session teaching pipeline."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from ilearn.core.datetime_utils import utc_now


class SchedulerEventLog:
    """Append-only JSONL of scheduler.dispatch events (does not touch session FSM)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, learner_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in learner_id)
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path / "scheduler_events.jsonl"

    def append(self, event_type: str, payload: dict[str, Any], learner_id: str) -> str:
        event_id = uuid4().hex
        row = {
            "event_id": event_id,
            "event_type": event_type,
            "learner_id": learner_id,
            "occurred_at": utc_now().isoformat(),
            "payload": payload,
        }
        with self._lock:
            path = self._path(learner_id)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return event_id

    def list_events(self, learner_id: str) -> list[dict[str, Any]]:
        path = self._path(learner_id)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def load_receipt(self, learner_id: str, receipt_id: str):
        from ilearn.scheduler.models import ProactiveDispatchReceipt

        for row in self.list_events(learner_id):
            if row.get("event_type") != "scheduler.dispatch":
                continue
            payload = row.get("payload") or {}
            if payload.get("receipt_id") == receipt_id:
                return ProactiveDispatchReceipt.model_validate(payload)
        raise KeyError(f"receipt not found: {receipt_id}")

    def list_dispatches(self, learner_id: str):
        from ilearn.scheduler.models import ProactiveDispatchReceipt

        out = []
        for row in self.list_events(learner_id):
            if row.get("event_type") != "scheduler.dispatch":
                continue
            out.append(ProactiveDispatchReceipt.model_validate(row.get("payload") or {}))
        return out

    def consumed_receipt_ids(self, learner_id: str) -> set[str]:
        ids: set[str] = set()
        for row in self.list_events(learner_id):
            if row.get("event_type") != "scheduler.consumed":
                continue
            payload = row.get("payload") or {}
            rid = payload.get("receipt_id")
            if rid:
                ids.add(str(rid))
        return ids

    def list_pending_receipts(self, learner_id: str):
        consumed = self.consumed_receipt_ids(learner_id)
        return [r for r in self.list_dispatches(learner_id) if r.receipt_id not in consumed]

    def list_learner_ids(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def read_learner(self, learner_id: str, *, days: int | None = None) -> list[dict[str, Any]]:
        rows = self.list_events(learner_id)
        if days is None:
            return rows
        from datetime import timedelta

        cutoff = utc_now() - timedelta(days=int(days))
        out = []
        for row in rows:
            raw = row.get("occurred_at")
            try:
                from datetime import datetime

                ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except Exception:
                out.append(row)
                continue
            if ts.tzinfo is None:
                from datetime import timezone

                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                out.append(row)
        return out

    def read_recent(self, *, days: int = 90) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for lid in self.list_learner_ids():
            rows.extend(self.read_learner(lid, days=days))
        return rows

    def list_by_type(self, event_type: str, *, days: int | None = None) -> list[dict[str, Any]]:
        rows = self.read_recent(days=days) if days is not None else []
        if days is None:
            for lid in self.list_learner_ids():
                rows.extend(self.list_events(lid))
        return [r for r in rows if r.get("event_type") == event_type]
