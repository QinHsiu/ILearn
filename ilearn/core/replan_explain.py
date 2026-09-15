"""P11 replan explanation chain (why replan + what changed)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.replan import (
    FRUSTRATION_THRESHOLD,
    replan_adjustments,
    should_replan,
)
from ilearn.core.schemas import DiagnosisReport, LearnerPortrait, LearningPlanReport


class ReplanExplanation(BaseModel):
    triggered: bool = False
    reasons: list[str] = Field(default_factory=list)
    adjustments: dict[str, Any] = Field(default_factory=dict)
    previous_goal: str | None = None
    new_goal: str | None = None
    frustration: float = 0.0
    hint_dependency: float = 0.0


def build_replan_explanation(
    *,
    portrait: LearnerPortrait | None,
    diagnosis: DiagnosisReport | None,
    previous_plan: LearningPlanReport | None = None,
    new_plan: LearningPlanReport | None = None,
) -> ReplanExplanation:
    if portrait is None or diagnosis is None:
        return ReplanExplanation(
            triggered=False,
            reasons=["缺少画像或诊断，按教师/家长手动重规划处理"],
            previous_goal=previous_plan.goal if previous_plan else None,
            new_goal=new_plan.goal if new_plan else None,
        )

    frustration = float(portrait.dimensions.emotional.get("frustration", 0.0) or 0.0)
    hint_dep = float(portrait.dimensions.behavioral.get("hint_dependency", 0.0) or 0.0)
    triggered = should_replan(portrait, diagnosis)
    reasons: list[str] = []
    if frustration >= FRUSTRATION_THRESHOLD:
        reasons.append(f"挫败感偏高（{frustration:.2f} ≥ {FRUSTRATION_THRESHOLD}），先降难度重建信心")
    if hint_dep >= 0.4:
        reasons.append(f"提示依赖偏高（{hint_dep:.2f}），增加口述与独立尝试比例")
    if "practice_probe_gap" in (diagnosis.flags or []):
        reasons.append("练习分与无提示探针掌握度落差过大，需探针复核")
    if not reasons and triggered:
        reasons.append("诊断标志触发重规划")
    if not triggered and not reasons:
        reasons.append("手动重规划：在现有证据上刷新学习计划")

    adjustments = replan_adjustments(diagnosis) if triggered else {}
    return ReplanExplanation(
        triggered=triggered,
        reasons=reasons,
        adjustments=adjustments,
        previous_goal=previous_plan.goal if previous_plan else None,
        new_goal=new_plan.goal if new_plan else None,
        frustration=frustration,
        hint_dependency=hint_dep,
    )
