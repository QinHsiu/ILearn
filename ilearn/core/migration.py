from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any
from uuid import uuid4

from ilearn.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class EvidenceMigrator:
    @staticmethod
    def migrate_evidence_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None
        out = dict(entry)
        try:
            if "confidence" not in out:
                out["confidence"] = 0.5
            if not out.get("evidence_id"):
                out["evidence_id"] = uuid4().hex
            if "lane" not in out:
                source = str(out.get("source_type") or "").casefold()
                out["lane"] = "probe" if source == "probe" else "practice"
            if "hint_level" not in out:
                hint_count = out.get("hint_count")
                if isinstance(hint_count, int) and hint_count > 0:
                    out["hint_level"] = "low"
            if "created_at" not in out and out.get("timestamp") is not None:
                out["created_at"] = out["timestamp"]
            for key in ("session_id", "item_id", "knowledge_id"):
                if not out.get(key):
                    return None
            if "correct" not in out:
                return None
            out["correct"] = bool(out["correct"])
            return out
        except Exception:
            logger.exception("evidence migrate failed; dropping entry")
            return None

    @staticmethod
    def migrate_evidence_log(evidence_log: list[Any]) -> list[dict[str, Any]]:
        migrated: list[dict[str, Any]] = []
        for row in evidence_log or []:
            if isinstance(row, dict):
                item = EvidenceMigrator.migrate_evidence_entry(row)
                if item is not None:
                    migrated.append(item)
            else:
                # already-modelled objects: dump if possible
                dump = getattr(row, "model_dump", None)
                if callable(dump):
                    item = EvidenceMigrator.migrate_evidence_entry(dump())
                    if item is not None:
                        migrated.append(item)
        return migrated

    @staticmethod
    def migrate_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
        data = deepcopy(payload)
        if "evidence_log" in data and isinstance(data["evidence_log"], list):
            data["evidence_log"] = EvidenceMigrator.migrate_evidence_log(
                data["evidence_log"]
            )
        return data
