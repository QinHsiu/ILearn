from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ilearn.core.schemas import GradeResult, KnowledgeMastery

# Chinese short labels for why suffixes
_ERROR_TAG_ZH = {
    "concept_gap": "概念缺口",
    "calc_error": "计算错误",
    "misread": "审题失误",
    "method_wrong": "方法不当",
    "incomplete": "步骤不完整",
}

_SOLO_ZH = {
    "prestructural": "SOLO前结构",
    "unistructural": "SOLO单点结构",
    "multistructural": "SOLO多点结构",
    "relational": "SOLO关联结构",
}

SOLO_LEVEL_KEYS = ("prestructural", "unistructural", "multistructural", "relational")


class ErrorType(Enum):
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    CARELESS = "careless"
    TRANSFER = "transfer"
    READING = "reading"


ERROR_TAG_TO_TYPE: dict[str, ErrorType] = {
    "concept_gap": ErrorType.CONCEPTUAL,
    "calc_error": ErrorType.PROCEDURAL,
    "misread": ErrorType.READING,
    "method_wrong": ErrorType.TRANSFER,
    "incomplete": ErrorType.PROCEDURAL,
}


@dataclass
class Enrichment:
    flags: list[str] = field(default_factory=list)
    why_suffix_by_knowledge_id: dict[str, str] = field(default_factory=dict)


def classify_solo_from_grades(grades: list[GradeResult]) -> str:
    if not grades:
        return "prestructural"
    correct = sum(1 for g in grades if g.final_correct)
    incorrect = len(grades) - correct
    any_tags = any(g.error_tags for g in grades)
    if incorrect == len(grades) and not any_tags:
        return "prestructural"
    if incorrect == len(grades) and any_tags:
        return "unistructural"
    if correct == len(grades) and len(grades) >= 2:
        return "relational"
    if correct > incorrect:
        return "multistructural"
    if any_tags:
        return "unistructural"
    return "prestructural"


def enrich_diagnosis(
    *,
    knowledge_mastery: list[KnowledgeMastery],
    grades: list[GradeResult],
) -> Enrichment:
    if not grades:
        return Enrichment()

    solo = classify_solo_from_grades(grades)
    flags: list[str] = [f"solo:{solo}"]

    seen_tags: list[str] = []
    for g in grades:
        for tag in g.error_tags:
            if tag in ERROR_TAG_TO_TYPE and tag not in seen_tags:
                seen_tags.append(tag)
    for tag in seen_tags[:5]:
        flags.append(f"rule:{tag}")

    suffixes: dict[str, str] = {}
    solo_zh = _SOLO_ZH.get(solo, f"SOLO{solo}")
    for km in knowledge_mastery:
        if km.level == "mastered":
            continue
        dominant = None
        if km.error_tag_counts:
            dominant = max(km.error_tag_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        parts = [solo_zh]
        if dominant and dominant in _ERROR_TAG_ZH:
            parts.append(f"规则偏向{_ERROR_TAG_ZH[dominant]}")
        suffixes[km.knowledge_id] = "；".join(parts)

    return Enrichment(flags=flags, why_suffix_by_knowledge_id=suffixes)
