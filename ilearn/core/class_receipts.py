"""Aggregate tier assignment receipts across class sessions."""

from __future__ import annotations

from typing import Any

from ilearn.core.schemas import SessionState
from ilearn.core.winbar_exports import assign_tiers_for_session
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore


def apply_tier_assign_and_save(
    store: SessionStore,
    session: SessionState,
    *,
    topic: str | None = None,
    students: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assign tiers for one session, persist papers + timeline, return API-shaped payload."""
    result = assign_tiers_for_session(session, topic=topic, students=students)
    meta = dict(session.metadata or {})
    meta["tier_papers"] = result["papers"]
    meta["tier_assignment_receipt"] = result["receipt"]
    timeline = list(meta.get("tier_assignment_timeline") or [])
    item_counts = {
        k: len(v.get("items") or []) for k, v in result["papers"].items()
    }
    timeline.insert(
        0,
        {
            **result["receipt"],
            "item_counts": item_counts,
        },
    )
    meta["tier_assignment_timeline"] = timeline[:20]
    session.metadata = meta
    store.save(session)
    return {
        "session_id": session.session_id,
        "receipt": result["receipt"],
        "paper_keys": list(result["papers"].keys()),
        "item_counts": item_counts,
        "timeline_len": len(meta["tier_assignment_timeline"]),
        "student_name": (session.profile.nickname or "").strip() or session.session_id[:8],
    }


def aggregate_class_assignment_timeline(
    *,
    sessions: SessionStore,
    relationships: RelationshipStore,
    teacher_id: str,
    class_id: str,
    limit: int = 30,
) -> dict[str, Any]:
    """Merge per-session tier timelines for one teacher class (newest first)."""
    session_ids = relationships.students_for_class(teacher_id, class_id)
    rows: list[dict[str, Any]] = []
    for sid in session_ids:
        try:
            session = sessions.load(sid)
        except FileNotFoundError:
            continue
        nickname = (session.profile.nickname or "").strip() or sid[:8]
        timeline = list((session.metadata or {}).get("tier_assignment_timeline") or [])
        for entry in timeline:
            if not isinstance(entry, dict):
                continue
            rows.append(
                {
                    "session_id": sid,
                    "student_name": nickname,
                    "assigned_at": entry.get("assigned_at"),
                    "topic": entry.get("topic"),
                    "item_counts": entry.get("item_counts") or {},
                    "receipt": {
                        k: entry.get(k)
                        for k in ("assigned_at", "topic", "teacher_note")
                        if entry.get(k) is not None
                    },
                }
            )
    rows.sort(key=lambda r: str(r.get("assigned_at") or ""), reverse=True)
    clipped = rows[: max(1, limit)]
    return {
        "teacher_id": teacher_id,
        "class_id": class_id,
        "count": len(clipped),
        "total_events": len(rows),
        "session_count": len(session_ids),
        "timeline": clipped,
    }


def batch_assign_class_tiers(
    *,
    sessions: SessionStore,
    relationships: RelationshipStore,
    teacher_id: str,
    class_id: str,
    session_ids: list[str] | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Assign consolidation papers to many class students; return batch receipt."""
    class_sids = set(relationships.students_for_class(teacher_id, class_id))
    if not class_sids:
        return {
            "teacher_id": teacher_id,
            "class_id": class_id,
            "assigned_count": 0,
            "failed": [],
            "results": [],
            "summary": "班级暂无绑定学生",
        }
    targets = list(session_ids) if session_ids else sorted(class_sids)
    results: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    for sid in targets:
        if sid not in class_sids:
            failed.append({"session_id": sid, "error": "not_in_class"})
            continue
        try:
            session = sessions.load(sid)
        except FileNotFoundError:
            failed.append({"session_id": sid, "error": "session_missing"})
            continue
        try:
            results.append(apply_tier_assign_and_save(sessions, session, topic=topic))
        except Exception as exc:  # noqa: BLE001 — batch continues on per-student failure
            failed.append({"session_id": sid, "error": str(exc)})
    names = [str(r.get("student_name") or "") for r in results]
    summary = (
        f"已为 {len(results)} 人布置巩固卷"
        + (f"：{'、'.join(names[:5])}" if names else "")
        + (f"；失败 {len(failed)} 人" if failed else "")
    )
    return {
        "teacher_id": teacher_id,
        "class_id": class_id,
        "assigned_count": len(results),
        "failed": failed,
        "results": results,
        "summary": summary,
    }
