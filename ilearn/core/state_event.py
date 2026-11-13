"""Hash-chained learner state events (aligns with event_log / GradingReceipt)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now

StateEventType = Literal[
    "mastery.update",
    "misconception.detected",
    "review.scheduled",
    "engagement.updated",
    "goal.set",
]


class StateEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    learner_id: str
    event_type: StateEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str = Field(default_factory=lambda: utc_now().isoformat())
    prev_state_hash: str = ""
    event_hash: str = ""

    def compute_event_hash(self) -> str:
        body = {
            "event_id": self.event_id,
            "learner_id": self.learner_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "occurred_at": self.occurred_at,
            "prev_state_hash": self.prev_state_hash,
        }
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def seal(self) -> StateEvent:
        sealed = self.model_copy(deep=True)
        sealed.event_hash = sealed.compute_event_hash()
        return sealed
