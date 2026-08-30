"""Audience-friendly summaries for parents and teachers."""

from __future__ import annotations

from typing import Any, Literal

from ilearn.core.schemas import DiagnosisReport

Audience = Literal["parent", "teacher"]

_ERROR_LABELS: dict[str, str] = {
    "concept_gap": "概念理解不清",
    "calc_error": "计算过程易错",
    "misread": "审题不够仔细",
    "method_wrong": "解题方法选择不当",
    "incomplete": "解题步骤不完整",
}


def generate_audience_summary(
    diagnosis: DiagnosisReport | None,
    enrichment: dict[str, Any] | None = None,
    *,
    audience: Audience = "parent",
) -> str:
    """Turn diagnosis/enrichment into actionable Chinese advice."""
    enrichment = enrichment or {}
    weak = list(enrichment.get("weak_skills") or [])
    if diagnosis is not None and not weak:
        weak = [
            row.knowledge_id
            for row in diagnosis.knowledge_mastery
            if row.level == "weak"
        ]
    attribution = enrichment.get("error_attribution") or {}
    top_errors = list(attribution.get("top_tags") or [])

    if not weak and not top_errors:
        if audience == "teacher":
            return "本轮测评未发现明显薄弱点，可安排拓展题或提高题巩固学习动机。"
        return "孩子目前掌握得不错，可以适当挑战更高难度的内容。"

    lines: list[str] = []
    if audience == "parent":
        lines.append("给家长的行动建议：")
        for skill in weak[:3]:
            lines.append(f"• 在「{skill}」上，建议每天花约5分钟完成2道专项练习。")
        if top_errors:
            labels = "、".join(_ERROR_LABELS.get(t, t) for t in top_errors[:3])
            lines.append(f"• 近期主要失分倾向：{labels}。练习时请先让孩子口述思路再动笔。")
        gaps = list(enrichment.get("prerequisite_gaps") or [])
        if gaps:
            lines.append(
                "• 建议先复习前置内容：" + "、".join(gaps[:3]) + "，再继续当前单元。"
            )
    else:
        lines.append("给教师的课堂建议：")
        for skill in weak[:5]:
            lines.append(f"• 关注「{skill}」：可用变式题做形成性抽查。")
        if top_errors:
            labels = "、".join(_ERROR_LABELS.get(t, t) for t in top_errors[:3])
            lines.append(f"• 班级/个例错误类型集中在：{labels}，可设计对应纠错微课。")
        if enrichment.get("learning_advice"):
            lines.append(f"• 系统建议：{enrichment['learning_advice']}")
    return "\n".join(lines)


def aggregate_error_attribution(grades: list[Any] | None) -> dict[str, Any]:
    """Aggregate existing GradeResult.error_tags into enrichment-friendly stats."""
    counts: dict[str, int] = {}
    if not grades:
        return {"counts": {}, "top_tags": [], "wrong_count": 0}
    wrong = 0
    for grade in grades:
        if getattr(grade, "final_correct", True):
            continue
        wrong += 1
        tags = list(getattr(grade, "error_tags", None) or [])
        if not tags:
            counts["unknown"] = counts.get("unknown", 0) + 1
            continue
        for tag in tags:
            key = str(tag)
            counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.keys(), key=lambda k: (-counts[k], k))
    return {"counts": counts, "top_tags": top[:5], "wrong_count": wrong}
