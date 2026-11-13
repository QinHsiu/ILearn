"""Scheduler data models — review items + proactive dispatch receipts."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now

DispatchTrigger = Literal["spaced_repetition", "engagement_drop", "goal_deviation"]


class ReviewItem(BaseModel):
    """Due review entry derived from LearnerState.review_schedule (+ meta)."""

    skill_id: str
    due_at: datetime
    interval_days: float = 1.0
    ease_factor: float = 2.5
    review_count: int = 0
    last_quality: int | None = None


class ProactiveDispatchReceipt(BaseModel):
    """Bypass scheduler receipt — written to event_log / receipts store, replayable."""

    receipt_id: str = Field(default_factory=lambda: f"rcpt-{uuid4().hex[:12]}")
    learner_id: str
    trigger: DispatchTrigger
    reason: str
    skill_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    state_version: int
    state_hash: str = ""
    scheduled_at: datetime = Field(default_factory=utc_now)
    # Backward-compatible single skill field used by older callers.
    skill_id: str | None = None
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        payload = self.model_dump_json(exclude={"receipt_hash"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal(self) -> ProactiveDispatchReceipt:
        sealed = self.model_copy(deep=True)
        if sealed.skill_id and sealed.skill_id not in sealed.skill_ids:
            sealed.skill_ids = [sealed.skill_id, *sealed.skill_ids]
        sealed.receipt_hash = sealed.compute_hash()
        return sealed
