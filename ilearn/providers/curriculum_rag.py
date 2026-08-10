"""Keyword RAG retriever over local curriculum source snippets (Phase 1)."""

from __future__ import annotations

from pathlib import Path

from ilearn.core.schemas import CurriculumCitation, StudentProfile
from ilearn.providers.retriever import (
    get_retriever,
    load_curriculum_sources,
    source_to_citation,
)

__all__ = [
    "CurriculumRagRetriever",
    "load_curriculum_sources",
    "source_to_citation",
]


class CurriculumRagRetriever:
    """Thin facade over the keyword retriever backend (default)."""

    def __init__(self, pilot_dir: str | Path, *, backend: str = "keyword") -> None:
        self._retriever = get_retriever(backend, pilot_dir)

    def retrieve(
        self,
        profile: StudentProfile,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[CurriculumCitation]:
        return self._retriever.retrieve(profile, query, top_k=top_k)
