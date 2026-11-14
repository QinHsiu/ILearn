"""Teaching skill models — induced from episodic experience (no LLM)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillParameter(BaseModel):
    name: str
    kind: Literal["hint_level", "strategy_choice"]
    default: Any | None = None


class TeachingSkill(BaseModel):
    skill_id: str
    structural_signature: list[str] = Field(default_factory=list)
    derived_from_episodic: list[str] = Field(default_factory=list)
    parameters: list[SkillParameter] = Field(default_factory=list)
    action_sequence: list[dict] = Field(default_factory=list)
    learner_segment: dict = Field(default_factory=dict)
    confidence: float = 0.0
    created_at: datetime | str = ""
    state_version_at_creation: int = 0
    invocation_count: int = 0
    success_count: int = 0
    status: Literal["active", "deprecated", "under_review"] = "under_review"

    def validate_skill(self) -> bool:
        return 0.0 <= self.confidence <= 1.0 and bool(self.action_sequence)
