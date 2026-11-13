"""L2 wiki page + skill-graph edge models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now


class WikiPage(BaseModel):
    """Human-readable knowledge page; agent-queryable via BM25."""

    page_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    body: str
    skill_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    life_stage: str | None = None
    grade: int | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def searchable_text(self) -> str:
        parts = [self.title, self.body, " ".join(self.skill_ids), " ".join(self.tags)]
        return "\n".join(p for p in parts if p)


class WikiEdge(BaseModel):
    """Undirected skill / relatedness edge between pages."""

    edge_id: str = Field(default_factory=lambda: uuid4().hex)
    left_page_id: str
    right_page_id: str
    relation: str = "shares_skill"
    skill_id: str | None = None
    weight: float = 1.0


class WikiHit(BaseModel):
    page: WikiPage
    score: float
    matched_skills: list[str] = Field(default_factory=list)
    via_graph: bool = False
