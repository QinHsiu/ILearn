"""Experience record / prior — read-only decision context (no LLM)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExperienceRecord(BaseModel):
    record_id: str
    learner_segment: dict[str, Any] = Field(default_factory=dict)
    situation: str
    strategy: str
    outcome: Literal["effective", "ineffective", "neutral"] = "neutral"
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = ""


class ExperiencePrior(BaseModel):
    """Injected into decision context; never selects the action itself."""

    situation: str | dict[str, Any] = ""
    recommended_strategy: str | None = None
    confidence: float = 0.0
    support: int = 0
    refs: list[ExperienceRecord] = Field(default_factory=list)
    # Backward-compatible fields used by MultiAgentOrchestrator._ctx
    records: list[ExperienceRecord] = Field(default_factory=list)
    experience_refs: list[str] = Field(default_factory=list)
