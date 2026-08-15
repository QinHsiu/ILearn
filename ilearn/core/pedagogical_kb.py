from __future__ import annotations

import copy
import json
from pathlib import Path

_ERROR_TAG_BUCKET = {
    "concept_gap": "conceptual",
    "calc_error": "procedural",
    "incomplete": "procedural",
    "method_wrong": "procedural",
    "misread": "metacognitive",
}

_BUILTIN = {
    "conceptual": {
        "default": [
            "回顾相关定义：这个概念的关键条件是什么？",
            "能不能用自己的话再说一遍这道题在问什么？",
        ]
    },
    "procedural": {
        "default": [
            "检查运算步骤：相同数位是否对齐？有没有漏步骤？",
            "换一种列式思路：先写已知，再求未知。",
        ]
    },
    "metacognitive": {
        "default": [
            "再读一遍题目，圈出所有已知条件和所求。",
            "如果现在自查，你最想先检查哪一步？",
        ]
    },
}


def _default_data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "pedagogical_strategies.json"


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _collect_phrases(bucket: dict) -> list[str]:
    """Collect phrase lists from a bucket: default first, then other keys sorted."""
    phrases: list[str] = []
    skill_keys = sorted(
        k
        for k, v in bucket.items()
        if k != "default"
        and isinstance(v, list)
        and all(isinstance(x, str) for x in v)
    )
    default = bucket.get("default")
    if isinstance(default, list) and all(isinstance(x, str) for x in default):
        phrases.extend(default)
    for key in skill_keys:
        phrases.extend(bucket[key])
    return phrases


def _load_strategies(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None
    return data


class PedagogicalKnowledgeBase:
    def __init__(self, data_path: str | Path | None = ...) -> None:
        self.strategies = copy.deepcopy(_BUILTIN)
        load_path: Path | None
        if data_path is ...:
            load_path = _default_data_path()
        elif data_path is None:
            load_path = None
        else:
            load_path = Path(data_path)
        if load_path is not None:
            loaded = _load_strategies(load_path)
            if loaded is not None:
                self.strategies = _deep_merge(self.strategies, loaded)

    def retrieve(self, error_tag: str | None, fail_streak: int = 0) -> str | None:
        bucket = _ERROR_TAG_BUCKET.get(error_tag or "", "metacognitive")
        phrases = _collect_phrases(self.strategies.get(bucket, {}))
        if not phrases:
            return None
        idx = min(max(fail_streak, 0), len(phrases) - 1)
        return phrases[idx]


_kb: PedagogicalKnowledgeBase | None = None


def default_kb() -> PedagogicalKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = PedagogicalKnowledgeBase()
    return _kb
