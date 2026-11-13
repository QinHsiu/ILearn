"""Proactive dispatch receipts — auditable, no LLM inside scheduler."""

from __future__ import annotations

import hashlib
import json
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now

DispatchTrigger = Literal["spaced_repetition", "engagement_drop", "goal_deviation"]


class ProactiveDispatchReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: uuid4().hex)
    learner_id: str
    trigger: DispatchTrigger
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    scheduled_at: str = Field(default_factory=lambda: utc_now().isoformat())
    state_version: int
    skill_id: str | None = None
    receipt_hash: str = ""

    def seal(self) -> ProactiveDispatchReceipt:
        sealed = self.model_copy(deep=True)
        body = sealed.model_dump(exclude={"receipt_hash"})
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
        sealed.receipt_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return sealed
