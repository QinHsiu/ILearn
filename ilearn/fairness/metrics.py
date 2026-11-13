"""Fairness audit report models — read-only comparison artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GroupComparison(BaseModel):
    attribute: str
    group_a: str
    group_b: str
    metric: str
    value_a: float
    value_b: float
    gap: float
    n_a: int
    n_b: int
    flagged: bool


class FairnessAuditReport(BaseModel):
    window_start: str
    window_end: str
    comparisons: list[GroupComparison] = Field(default_factory=list)
    flagged_count: int = 0
    config: dict = Field(default_factory=dict)
