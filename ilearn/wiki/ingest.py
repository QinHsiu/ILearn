"""Ingest curriculum sources + concept markdown into L2 wiki."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ilearn.providers.retriever import load_curriculum_sources
from ilearn.wiki.models import WikiPage
from ilearn.wiki.store import WikiStore

_SKILL_FROM_KEYWORDS = re.compile(r"[\w\u4e00-\u9fff]+")


def _stable_page_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"wiki_{digest[:16]}"


def _skills_from_keywords(keywords: list[str]) -> list[str]:
    skills: list[str] = []
    for kw in keywords:
        token = "".join(_SKILL_FROM_KEYWORDS.findall(kw))
        if token:
            skills.append(f"kw:{token.casefold()}")
    return skills


def pages_from_curriculum_sources(pilot_dir: str | Path) -> list[WikiPage]:
    pages: list[WikiPage] = []
    for entry in load_curriculum_sources(pilot_dir):
        source_id = str(entry.get("source_id") or entry.get("title") or "unknown")
        keywords = list(entry.get("keywords") or [])
        skills = _skills_from_keywords(keywords)
        if entry.get("life_stage"):
            skills.append(f"stage:{entry['life_stage']}")
        # Prefer explicit skill aliases from title tokens
        title = str(entry.get("title") or source_id)
        for tok in _SKILL_FROM_KEYWORDS.findall(title):
            if len(tok) >= 2:
                skills.append(f"title:{tok.casefold()}")
        body = str(entry.get("excerpt") or "")
        if keywords:
            body = body + "\n\n关键词：" + "、".join(keywords)
        pages.append(
            WikiPage(
                page_id=_stable_page_id("curriculum", source_id),
                title=title,
                body=body,
                skill_ids=sorted(set(skills)),
                tags=keywords,
                source_refs=[source_id],
                life_stage=entry.get("life_stage"),
                grade=entry.get("grade"),
                metadata={"kind": "curriculum_source", "region": entry.get("region")},
            )
        )
    return pages


def pages_from_concept_assets(pilot_dir: str | Path) -> list[WikiPage]:
    concept_dir = Path(pilot_dir) / "assets" / "concept"
    if not concept_dir.is_dir():
        return []
    pages: list[WikiPage] = []
    for path in sorted(concept_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = path.stem
        for line in text.splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip() or title
                break
        skill = f"concept:{path.stem}"
        pages.append(
            WikiPage(
                page_id=_stable_page_id("concept", path.stem),
                title=title,
                body=text,
                skill_ids=[skill, f"kw:{path.stem}"],
                tags=[path.stem, "concept"],
                source_refs=[f"concept:{path.name}"],
                metadata={"kind": "concept_card", "path": str(path.name)},
            )
        )
    return pages


def ingest_pilot_wiki(store: WikiStore, pilot_dir: str | Path) -> dict[str, int]:
    pages = pages_from_curriculum_sources(pilot_dir) + pages_from_concept_assets(pilot_dir)
    n = store.upsert_many(pages)
    edges = store.rebuild_skill_graph()
    return {"pages": n, "edges_added": edges}
