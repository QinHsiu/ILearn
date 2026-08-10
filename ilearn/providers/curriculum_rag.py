"""Keyword RAG retriever over local curriculum source snippets (Phase 1)."""

from __future__ import annotations

import json
import re
from pathlib import Path

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


class CurriculumRagRetriever:
    """Retrieve curriculum citations via stdlib token-overlap scoring."""

    def __init__(self, pilot_dir: str | Path) -> None:
        self._sources = load_curriculum_sources(pilot_dir)

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

        return [_to_citation(entry) for _, entry in selected]


def source_to_citation(entry: dict) -> CurriculumCitation:
    return _to_citation(entry)


def _to_citation(entry: dict) -> CurriculumCitation:
    source_id = entry.get("source_id", entry.get("citation_id", "unknown"))
    return CurriculumCitation(
        citation_id=source_id,
        title=entry.get("title", ""),
        excerpt=entry.get("excerpt", ""),
        source_label=entry.get("source_label", "北京·人教·小学数学"),
    )
