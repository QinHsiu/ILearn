"""Shared assessment window for client countdown and server submit validation."""

from __future__ import annotations

from datetime import datetime, timezone

# Matches frontend ASSESSMENT_SECONDS (150 minutes).
ASSESSMENT_TIMEOUT_SECONDS = 150 * 60


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def assessment_started_at(session) -> str | None:
    raw = session.metadata.get("assessment_started_at")
    return str(raw) if raw else None


def mark_assessment_started(session) -> None:
    if not assessment_started_at(session):
        session.metadata["assessment_started_at"] = utc_now_iso()


def assessment_elapsed_seconds(session) -> float | None:
    started = assessment_started_at(session)
    if not started:
        return None
    try:
        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - start_dt
        return max(0.0, delta.total_seconds())
    except ValueError:
        return None


def is_assessment_timed_out(session) -> bool:
    elapsed = assessment_elapsed_seconds(session)
    if elapsed is None:
        return False
    return elapsed > ASSESSMENT_TIMEOUT_SECONDS


def apply_submit_timeout(session, paper_items: list) -> bool:
    """If past the assessment window, flag unanswered items and record timeout."""
    if not is_assessment_timed_out(session):
        return False
    answered_ids = {a.item_id for a in session.answers}
    unanswered = [item.id for item in paper_items if item.id not in answered_ids]
    session.metadata["assessment_timed_out"] = True
    session.metadata["assessment_timeout_unanswered"] = unanswered
    return True
