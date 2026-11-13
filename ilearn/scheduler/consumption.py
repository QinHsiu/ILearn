"""Dispatch consumption records — link learner behavior back to receipts."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from ilearn.core.datetime_utils import utc_now

ConsumptionOutcome = Literal["responded", "expired", "dismissed"]


class DispatchConsumption(BaseModel):
    """回执消费记录：与 scheduler.dispatch 通过 receipt_id 关联。"""

    consumption_id: str = Field(default_factory=lambda: f"cons-{uuid4().hex[:12]}")
    receipt_id: str
    learner_id: str
    outcome: ConsumptionOutcome
    quality: int | None = None  # SM-2 quality 0-5; None for expired/dismissed
    consumed_at: datetime = Field(default_factory=utc_now)
    evidence_refs: list[str] = Field(default_factory=list)
    # Skills taken from the matched receipt — needed for apply_consumption feedback
    skill_ids: list[str] = Field(default_factory=list)
    consumption_hash: str = ""

    def compute_hash(self) -> str:
        payload = self.model_dump_json(exclude={"consumption_hash"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal(self) -> DispatchConsumption:
        sealed = self.model_copy(deep=True)
        sealed.consumption_hash = sealed.compute_hash()
        return sealed

    @model_validator(mode="after")
    def _auto_seal(self) -> DispatchConsumption:
        if not self.consumption_hash:
            self.consumption_hash = self.compute_hash()
        return self
