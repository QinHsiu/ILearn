"""Resolve internal knowledge/skill ids to parent-facing Chinese labels."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_INTERNAL_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_GENERIC_FALLBACK = "一个需要加强的知识点"


def looks_like_internal_id(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return False
    return bool(_INTERNAL_ID.match(text))


def _repo_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


@lru_cache(maxsize=1)
def _pilot_knowledge_names() -> dict[str, str]:
    path = _repo_data_dir() / "pilot" / "knowledge.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return {}
    return {
        str(row["id"]): str(row["name"])
        for row in rows
        if isinstance(row, dict) and row.get("id") and row.get("name")
    }


@lru_cache(maxsize=1)
def _cognitive_skill_names() -> dict[str, str]:
    path = _repo_data_dir() / "cognitive_skills.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    skills = payload.get("skills") if isinstance(payload, dict) else None
    if not isinstance(skills, list):
        return {}
    return {
        str(row["skill_id"]): str(row["name"])
        for row in skills
        if isinstance(row, dict) and row.get("skill_id") and row.get("name")
    }


def mastery_name_map(diagnosis: Any | None) -> dict[str, str]:
    if diagnosis is None:
        return {}
    rows = getattr(diagnosis, "knowledge_mastery", None) or []
    return {
        str(row.knowledge_id): str(row.knowledge_name)
        for row in rows
        if getattr(row, "knowledge_id", None) and getattr(row, "knowledge_name", None)
    }


def resolve_knowledge_label(
    knowledge_id: str,
    *,
    mastery_names: dict[str, str] | None = None,
    fallback: str = _GENERIC_FALLBACK,
) -> str:
    kid = (knowledge_id or "").strip()
    if not kid:
        return fallback

    names = mastery_names or {}
    if kid in names and names[kid].strip():
        return names[kid].strip()

    pilot = _pilot_knowledge_names()
    if kid in pilot:
        return pilot[kid]

    cognitive = _cognitive_skill_names()
    if kid in cognitive:
        return cognitive[kid]

    if looks_like_internal_id(kid):
        return fallback
    return kid


def resolve_knowledge_labels(
    ids: list[str],
    *,
    mastery_names: dict[str, str] | None = None,
    dedupe: bool = True,
) -> list[str]:
    resolved = [
        resolve_knowledge_label(item, mastery_names=mastery_names) for item in ids
    ]
    if not dedupe:
        return resolved
    return list(dict.fromkeys(resolved))
