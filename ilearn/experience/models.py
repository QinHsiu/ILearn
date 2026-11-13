"""Experience record / prior — read-only decision context (no LLM)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExperienceRecord(BaseModel):
    record_id: str
    learner_segment: dict[str, Any] = Field(default_factory=dict)
    situation: str
    structural_signature: list[str] = Field(default_factory=list)
    strategy: str
    outcome: Literal["effective", "ineffective", "neutral"] = "neutral"
    form: Literal["episodic", "distilled"] = "episodic"
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime | str = ""
    state_version_at_creation: int = 0
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    derived_from: list[str] = Field(default_factory=list)

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_created_at(cls, value: Any) -> Any:
        if value is None or value == "":
            return ""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value
        return value


class ExperiencePrior(BaseModel):
    """Injected into decision context; never selects the action itself."""

    situation: str | dict[str, Any] = ""
    recommended_strategy: str | None = None
    confidence: float = 0.0
    weighted_confidence: float = 0.0
    support: int = 0
    recency_score: float = 1.0
    version_distance: int = 0
    refs: list[ExperienceRecord] = Field(default_factory=list)
    records: list[ExperienceRecord] = Field(default_factory=list)
    experience_refs: list[str] = Field(default_factory=list)
    structural_fallback: bool = False
