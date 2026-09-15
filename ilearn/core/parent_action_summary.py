"""Parent one-minute actionable summary (rule-based, no LLM)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParentActionSummary(BaseModel):
    headline: str
    wins: list[str] = Field(default_factory=list)
    focus: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


def build_parent_action_summary(
    *,
    child_name: str,
    current_mastery: float,
    mastery_change: float,
    weak_skills: list[str],
    strong_hints: list[str] | None = None,
) -> ParentActionSummary:
    name = child_name or "孩子"
    pct = int(round(max(0.0, min(1.0, current_mastery)) * 100))
    change_pp = int(round(mastery_change * 100))

    if change_pp > 0:
        headline = f"{name}本周掌握度约 {pct}%，比上次提升约 {change_pp} 个百分点"
    elif change_pp < 0:
        headline = f"{name}本周掌握度约 {pct}%，需要一点点加练巩固"
    else:
        headline = f"{name}本周掌握度约 {pct}%，保持节奏最重要"

    wins: list[str] = []
    if change_pp > 0:
        wins.append(f"掌握度有进步（+{change_pp}pp），值得当面表扬")
    if strong_hints:
        wins.extend([f"表现不错：{s}" for s in strong_hints[:2]])
    if not wins:
        wins.append("完成了诊断与计划，已经迈出关键一步")

    focus = [f"需要加强：{s}" for s in weak_skills[:2]]
    if not focus:
        focus = ["整体较稳，可挑战稍难一点的变式题"]

    actions: list[str] = []
    if weak_skills:
        topic = weak_skills[0]
        actions.append(f"今晚用生活例子聊 5 分钟「{topic}」（买菜找零、分披萨等）")
        actions.append("看一眼学习报告里的薄弱点，陪孩子口述解题思路，不直接报答案")
        if len(weak_skills) > 1:
            actions.append(f"把「{weak_skills[1]}」记到本周盯梢清单，明天再练一道同类题")
    else:
        actions.append("选 1 道稍难练习，让孩子讲给家长听（费曼法）")
    actions.append("保持固定小块时间，比一次刷很多题更有效")

    return ParentActionSummary(
        headline=headline,
        wins=wins[:2],
        focus=focus[:2],
        actions=actions[:3],
    )


def action_summary_as_dict(summary: ParentActionSummary) -> dict[str, Any]:
    return summary.model_dump()
