"""Swappable curriculum retriever backends (Phase 2c)."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Protocol

from ilearn.core.schemas import CurriculumCitation, StudentProfile

_HASH_VECTOR_DIM = 256

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


def _hash_bigram_embed(text: str, *, dim: int = _HASH_VECTOR_DIM) -> list[float]:
    """Embed text via hashed character bigrams into a dense unit vector."""
    vec = [0.0] * dim
    normalized = text.casefold().strip()
    for index in range(len(normalized) - 1):
        bigram = normalized[index : index + 2]
        digest = hashlib.md5(bigram.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % dim
        vec[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in vec))
    if norm > 0:
        vec = [value / norm for value in vec]
    return vec


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _entry_doc_text(entry: dict) -> str:
    return " ".join(
        [
            entry.get("title", ""),
            entry.get("excerpt", ""),
            " ".join(entry.get("keywords", [])),
        ]
    )


def _filter_entries(profile: StudentProfile, sources: list[dict]) -> list[dict]:
    filtered: list[dict] = []
    for entry in sources:
        if entry.get("grade") != profile.grade:
            continue
        region = entry.get("region", "")
        if _is_beijing(profile.region) and not _is_beijing(region):
            continue
        filtered.append(entry)
    return filtered


class HashVectorCurriculumRetriever:
    """Retrieve curriculum citations via stdlib hashed bigram vectors."""

    def __init__(self, sources: list[dict]) -> None:
        self._sources = sources
        self._vectors: list[tuple[list[float], dict]] = [
            (_hash_bigram_embed(_entry_doc_text(entry)), entry) for entry in sources
        ]

    def retrieve(
        self,
        profile: StudentProfile,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[CurriculumCitation]:
        allowed_ids = {entry.get("source_id") for entry in _filter_entries(profile, self._sources)}
        query_vec = _hash_bigram_embed(query)
        candidates: list[tuple[float, dict]] = []

        for vec, entry in self._vectors:
            source_id = entry.get("source_id")
            if source_id not in allowed_ids:
                continue
            score = _cosine_similarity(query_vec, vec)
            candidates.append((score, entry))

        candidates.sort(key=lambda pair: (-pair[0], pair[1].get("source_id", "")))
        selected = candidates[:top_k]

        if not _is_beijing(profile.region):
            selected = selected[:2]

        return [source_to_citation(entry) for _, entry in selected]


class QdrantCurriculumRetriever:
    """Optional Qdrant backend stub (requires qdrant-client in a future phase)."""

    def __init__(self, sources: list[dict]) -> None:
        self._sources = sources

    def retrieve(
        self,
        profile: StudentProfile,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[CurriculumCitation]:
        raise NotImplementedError(
            "Install qdrant-client and configure ILEARN_QDRANT_URL — Phase 2c stub"
        )


def get_retriever(backend: str, pilot_dir: Path | str) -> CurriculumRetriever:
    sources = load_curriculum_sources(pilot_dir)
    if backend == "keyword":
        return KeywordCurriculumRetriever(sources)
    if backend == "hash_vector":
        return HashVectorCurriculumRetriever(sources)
    if backend == "qdrant":
        return QdrantCurriculumRetriever(sources)
    raise ValueError(f"unknown retriever backend: {backend}")
