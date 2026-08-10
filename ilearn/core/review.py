"""SM-2 spaced repetition scheduling for knowledge review."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel

__all__ = ["ReviewState", "due_knowledge_ids", "sm2_update"]


class ReviewState(BaseModel):
    """Per-knowledge SM-2 scheduling state."""

    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    due_date: date | None = None


def sm2_update(state: ReviewState, quality: int) -> ReviewState:
    """SuperMemo-2 update; quality 0-5 (3+ = success)."""
    if quality < 3:
        return ReviewState(
            ease_factor=max(1.3, state.ease_factor - 0.2),
            interval_days=1,
            repetitions=0,
            due_date=date.today() + timedelta(days=1),
        )
    ef = state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    reps = state.repetitions + 1
    if reps == 1:
        interval = 1
    elif reps == 2:
        interval = 6
    else:
        interval = round(state.interval_days * ef)
    return ReviewState(
        ease_factor=max(1.3, ef),
        interval_days=interval,
        repetitions=reps,
        due_date=date.today() + timedelta(days=interval),
    )


def due_knowledge_ids(portrait: Any, today: date) -> list[str]:
    """Return knowledge ids whose spaced review is due on or before ``today``."""
    return [
        kid
        for kid, rs in portrait.review_states.items()
        if rs.due_date is not None and rs.due_date <= today
    ]
