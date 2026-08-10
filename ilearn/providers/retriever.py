"""Swappable curriculum retriever backends (Phase 2c)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from ilearn.core.schemas import CurriculumCitation, StudentProfile

_TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+")


def _tokenize(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_PATTERN.findall(text) if token.strip()}


def _score(query_tokens: set[str], doc_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens)


def _is_beijing(region: str) -> bool:
    normalized = region.strip().casefold()
    return normalized in ("北京", "beijing")


def load_curriculum_sources(pilot_dir: str | Path) -> list[dict]:
    path = Path(pilot_dir) / "curriculum_sources.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def source_to_citation(entry: dict) -> CurriculumCitation:
    source_id = entry.get("source_id", entry.get("citation_id", "unknown"))
    return CurriculumCitation(
        citation_id=source_id,
        source_id=source_id,
        title=entry.get("title", ""),
        excerpt=entry.get("excerpt", ""),
        source_label=entry.get("source_label", "北京·人教·小学数学"),
    )


class CurriculumRetriever(Protocol):
    def retrieve(
        self,
        profile: StudentProfile,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[CurriculumCitation]: ...


class KeywordCurriculumRetriever:
    """Retrieve curriculum citations via stdlib token-overlap scoring."""

    def __init__(self, sources: list[dict]) -> None:
        self._sources = sources

    def retrieve(
        self,
        profile: StudentProfile,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[CurriculumCitation]:
        query_tokens = _tokenize(query)
        candidates: list[tuple[float, dict]] = []

        for entry in self._sources:
            if entry.get("grade") != profile.grade:
                continue
            region = entry.get("region", "")
            if _is_beijing(profile.region) and not _is_beijing(region):
                continue

            doc_text = " ".join(
                [
                    entry.get("title", ""),
                    entry.get("excerpt", ""),
                    " ".join(entry.get("keywords", [])),
                ]
            )
            doc_tokens = _tokenize(doc_text)
            score = _score(query_tokens, doc_tokens)
            candidates.append((score, entry))

        candidates.sort(key=lambda pair: (-pair[0], pair[1].get("source_id", "")))
        selected = candidates[:top_k]

        if not _is_beijing(profile.region):
            selected = selected[:2]

        return [source_to_citation(entry) for _, entry in selected]


def get_retriever(backend: str, pilot_dir: Path | str) -> CurriculumRetriever:
    if backend == "keyword":
        return KeywordCurriculumRetriever(load_curriculum_sources(pilot_dir))
    raise ValueError(f"unknown retriever backend: {backend}")
