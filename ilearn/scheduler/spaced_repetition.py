"""SM-2 spaced repetition — pure functions for audit replay (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class SM2State:
    review_count: int = 0
    ease_factor: float = 2.5
    interval_days: float = 1.0


def sm2_update(state: SM2State, quality: int) -> SM2State:
    """SM-2 pure function. quality ∈ [0,5]. No DB, clock, or randomness."""
    if not 0 <= int(quality) <= 5:
        raise ValueError(f"quality must be in [0,5], got {quality}")
    quality = int(quality)
    if quality < 3:
        return SM2State(review_count=0, ease_factor=state.ease_factor, interval_days=1.0)
    ef = max(
        1.3,
        state.ease_factor
        + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    if state.review_count == 0:
        interval = 1.0
    elif state.review_count == 1:
        interval = 6.0
    else:
        interval = round(state.interval_days * ef, 1)
    return SM2State(state.review_count + 1, round(ef, 3), interval)


def next_due(state: SM2State, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now + timedelta(days=float(state.interval_days))


# Alias kept for existing call sites.
due_at = next_due


def quality_from_mastery(mastery: float) -> int:
    """Map mastery 0–1 → SM-2 quality 0–5."""
    if mastery < 0.2:
        return 1
    if mastery < 0.4:
        return 2
    if mastery < 0.6:
        return 3
    if mastery < 0.8:
        return 4
    return 5
