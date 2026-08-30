"""Skill-level intervention snippets for Tutor / hints."""

from __future__ import annotations

from typing import Any

# Keys may be cognitive skill_id or legacy knowledge_id.
INTERVENTION_MAP: dict[str, dict[str, str]] = {
    "frac_add_same": {
        "hint": "同分母加减时，分母不变，只把分子相加减。",
        "micro_lesson": "回顾：同分母分数加减法。",
    },
    "frac_mult": {
        "hint": "分数乘法：分子乘分子、分母乘分母，能约分先约分。",
        "micro_lesson": "回顾：分数乘法意义与计算。",
    },
    "frac_div": {
        "hint": "分数除法：除以一个数等于乘它的倒数。",
        "micro_lesson": "回顾：分数除法与倒数。",
    },
    "frac_meaning_001": {
        "hint": "先明确把单位‘1’平均分成几份，再看取了几份。",
        "micro_lesson": "回顾：分数单位。",
    },
    "frac_meaning_003": {
        "hint": "用分数表示部分时，分母是总份数，分子是所取份数。",
        "micro_lesson": "回顾：用分数表示部分。",
    },
    "find_common_denominator": {
        "hint": "找公分母时，试试看两个分母的最小公倍数是多少？",
        "micro_lesson": "公分母就是几个分数分母的最小公倍数。",
    },
    "rect_area": {
        "hint": "长方形面积 = 长 × 宽，注意单位是否统一。",
        "micro_lesson": "回顾：长方形面积公式。",
    },
    "mult_3digit": {
        "hint": "三位数乘两位数：分步乘再相加，注意对齐数位。",
        "micro_lesson": "回顾：多位数乘法竖式。",
    },
}


def lookup_intervention(*skill_keys: str | None) -> dict[str, str] | None:
    """Return first matching intervention for any provided skill key."""
    for key in skill_keys:
        if not key:
            continue
        hit = INTERVENTION_MAP.get(key)
        if hit:
            return dict(hit)
    return None


def intervention_hint_for_item(item: Any, error_tag: str | None = None) -> str | None:
    """Best-effort hint from item knowledge_ids (+ optional error context)."""
    del error_tag
    kids = list(getattr(item, "knowledge_ids", None) or [])
    hit = lookup_intervention(*[str(k) for k in kids])
    if hit:
        return hit.get("hint")
    return None
