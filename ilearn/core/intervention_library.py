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

# Optional tiered strategies keyed by the same skill ids.
TIERED_INTERVENTIONS: dict[str, dict[str, dict[str, Any]]] = {
    "frac_add_same": {
        "tier_1": {
            "type": "micro_practice",
            "content": "完成 3 道同分母加减题，限时 2 分钟",
            "hint": "回忆：分母不变，分子相加减",
        },
        "tier_2": {
            "type": "concept_review",
            "content": "回顾同分母加减意义 + 5 道渐进练习",
            "hint": INTERVENTION_MAP["frac_add_same"]["hint"],
        },
        "tier_3": {
            "type": "prerequisite_rebuild",
            "content": "先巩固分数意义，再回到同分母加减",
            "prerequisite_chain": ["frac_meaning_001", "frac_add_same"],
            "hint": "从分数单位重新理解‘同样多的一份’",
        },
    },
    "frac_mult": {
        "tier_1": {
            "type": "micro_practice",
            "content": "完成 3 道分数乘法基础题",
            "hint": "能约分先约分，再乘",
        },
        "tier_2": {
            "type": "concept_review",
            "content": "回顾分数乘法意义 + 变式练习",
            "hint": INTERVENTION_MAP["frac_mult"]["hint"],
        },
        "tier_3": {
            "type": "prerequisite_rebuild",
            "content": "先复习同分母加减与分数意义，再学乘法",
            "prerequisite_chain": ["frac_add_same", "frac_mult"],
            "hint": "乘法表示‘求一个数的几分之几’",
        },
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


def get_tiered_intervention(
    skill_id: str | None, mastery: float
) -> dict[str, Any] | None:
    """Return tiered intervention by mastery; None if mastery >= 0.8."""
    if not skill_id or mastery >= 0.8:
        return None
    if mastery >= 0.6:
        tier = "tier_1"
    elif mastery >= 0.4:
        tier = "tier_2"
    else:
        tier = "tier_3"
    table = TIERED_INTERVENTIONS.get(skill_id)
    if table and tier in table:
        out = dict(table[tier])
        out["tier"] = tier
        out["skill_id"] = skill_id
        out["mastery"] = mastery
        return out
    # Fallback to flat map as tier_2-style concept review
    flat = INTERVENTION_MAP.get(skill_id)
    if not flat:
        return None
    return {
        "tier": tier,
        "skill_id": skill_id,
        "mastery": mastery,
        "type": "concept_review",
        "content": flat.get("micro_lesson") or flat.get("hint") or "",
        "hint": flat.get("hint") or "",
    }
