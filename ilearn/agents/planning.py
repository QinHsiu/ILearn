"""Planning agent — learning recommendations and practice-loop trigger."""

from __future__ import annotations

import datetime
from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.learning_style import LearningStyleInferer
from ilearn.core.planning import Planner
from ilearn.core.schemas import (
    DiagnosisReport,
    LearningPlanReport,
    PlanVersion,
    StudentProfile,
)
from ilearn.providers.curriculum import CurriculumProvider

__all__ = ["PlanningAgent", "max_practice_loops", "should_enter_practice_loop"]

_MAX_LOOPS = 2
_REVIEW_INTERVALS = (1, 3, 7, 15, 30)

_STYLE_MAPPING: dict[str, dict[str, Any]] = {
    "visual": {
        "material_type": ["diagram", "chart", "interactive_geometry"],
        "suggestion": "推荐使用图形化材料辅助理解",
    },
    "auditory": {
        "material_type": ["audio_explanation", "read_aloud"],
        "suggestion": "推荐听讲解或跟读例题",
    },
    "kinesthetic": {
        "material_type": ["simulation", "drag_drop", "manipulative"],
        "suggestion": "推荐动手操作类练习",
    },
    "reading": {
        "material_type": ["worked_example", "text_summary"],
        "suggestion": "推荐文字例题与总结笔记",
    },
}

_ERROR_CORRECTION: dict[str, str] = {
    "concept_gap": "针对概念混淆：先用自己的话解释定义，再做2道概念辨析题。",
    "calc_error": "针对计算失误：限时完成3道同类计算，每题验算一步。",
    "misread": "针对审题不清：读题后先圈出已知与所求，再动笔。",
    "method_wrong": "针对方法不当：对比两种列式，说明为何选用其中一种。",
    "incomplete": "针对步骤不完整：按标准步骤模板重写解题过程。",
}


def _error_correction_instruction(tag: str) -> str:
    return _ERROR_CORRECTION.get(tag, f"针对错误类型「{tag}」完成2道纠错练习。")


def max_practice_loops(profile: StudentProfile) -> int:
    return 4 if profile.learning_difficulty else _MAX_LOOPS


def should_enter_practice_loop(
    diagnosis: DiagnosisReport,
    loop_count: int,
    *,
    profile: StudentProfile | None = None,
) -> bool:
    if loop_count >= (max_practice_loops(profile) if profile else _MAX_LOOPS):
        return False
    return any(m.level == "weak" for m in diagnosis.knowledge_mastery)


class PlanningAgent:
    name = "planning"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._planner = Planner(curriculum)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.diagnosis is None:
            raise ValueError("PlanningAgent requires diagnosis in context")
        plan = self._planner.plan(ctx.profile, ctx.diagnosis, portrait=ctx.portrait)
        plan_history_append: list[PlanVersion] = []
        if ctx.plan is not None:
            superseded_plan = ctx.plan.model_copy(update={"status": "superseded"})
            plan_history_append.append(
                PlanVersion(
                    version=ctx.plan.version,
                    status="superseded",
                    plan=superseded_plan,
                )
            )
            plan = plan.model_copy(
                update={"version": ctx.plan.version + 1, "status": "draft"}
            )
        else:
            plan = plan.model_copy(update={"version": 1, "status": "draft"})
        citations = ctx.metadata.get("citations", [])
        if citations:
            plan.markdown += "\n\n## \u8bfe\u6807\u4f9d\u636e\n" + "\n".join(
                f"- {c.title}\uff1a{c.excerpt}" for c in citations[:3]
            )

        enrichment = ctx.metadata.get("diagnosis_enrichment") or {}
        enrichment_dict = enrichment if isinstance(enrichment, dict) else {}
        behavior = ctx.metadata.get("behavior")
        learning_style: str | None = None
        if isinstance(behavior, dict) and behavior:
            learning_style = LearningStyleInferer().infer(behavior)
        if learning_style:
            scientific = self.generate_personalized_plan(
                ctx.diagnosis,
                learning_style,
                enrichment=enrichment_dict,
                profile=ctx.profile,
            )
        else:
            scientific = self.generate_scientific_plan(
                ctx.diagnosis,
                ctx.profile,
                enrichment=enrichment_dict,
            )
        plan = plan.model_copy(
            update={"markdown": plan.markdown + self._scientific_markdown(scientific)}
        )

        should_loop = should_enter_practice_loop(
            ctx.diagnosis, ctx.loop_count, profile=ctx.profile
        )
        next_phase = SessionPhase.PRACTICE_LOOP if should_loop else SessionPhase.PLAN
        return AgentResult(
            phase=next_phase,
            payload={
                "plan": plan,
                "should_loop": should_loop,
                "plan_history_append": plan_history_append,
                "scientific_plan": scientific,
            },
        )

    def generate_personalized_plan(
        self,
        diagnosis: DiagnosisReport,
        learning_style: str,
        *,
        enrichment: dict[str, Any] | None = None,
        profile: StudentProfile | None = None,
    ) -> dict[str, Any]:
        """Scientific plan plus learning-style material adaptation."""
        base_profile = profile or StudentProfile(region="北京", grade=5, age=11)
        plan = self.generate_scientific_plan(
            diagnosis, base_profile, enrichment=enrichment
        )
        adaptation = dict(
            _STYLE_MAPPING.get(learning_style, _STYLE_MAPPING["reading"])
        )
        plan["learning_style"] = learning_style
        plan["style_adaptation"] = adaptation
        return plan

    def generate_scientific_plan(
        self,
        diagnosis: DiagnosisReport,
        student_profile: StudentProfile,
        *,
        enrichment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build Feynman / review / spaced / Socratic tasks (PlanDay unchanged)."""
        del student_profile  # reserved for future personalization
        enrichment = enrichment or {}
        data_status = enrichment.get("data_status") or "ok"
        if data_status in {"insufficient_data", "limited_data"}:
            return {
                "tasks": [],
                "review_schedule": [],
                "learning_methods": [],
                "estimated_total_hours": 0.0,
                "status": "pending",
                "message": "诊断数据不足，无法生成个性化计划。请先完成更多题目。",
                "recommendation": "建议完成至少5道题目后重新生成计划。",
            }

        weak_skills = list(enrichment.get("weak_skills") or [])
        if not weak_skills:
            weak_skills = [
                row.knowledge_id
                for row in diagnosis.knowledge_mastery
                if row.level == "weak"
            ]
        gaps = list(enrichment.get("prerequisite_gaps") or [])
        if not weak_skills and not gaps:
            return {
                "tasks": [],
                "review_schedule": [],
                "learning_methods": ["maintenance"],
                "estimated_total_hours": 0.0,
                "status": "completed",
                "message": "暂无薄弱知识点，继续保持当前学习节奏！",
                "recommendation": "建议挑战更高难度题目。",
            }

        plan: dict[str, Any] = {
            "tasks": [],
            "review_schedule": [],
            "learning_methods": [],
            "estimated_total_hours": 0.0,
            "status": "ready",
        }

        for skill in weak_skills:
            plan["tasks"].append(
                {
                    "type": "feynman",
                    "skill": skill,
                    "instruction": (
                        f"\u8bf7\u5c1d\u8bd5\u7528\u4f60\u81ea\u5df1\u7684\u8bdd\u5411\u522b\u4eba\u89e3\u91ca"
                        f"\u201c{skill}\u201d\u7684\u6982\u5ff5\uff0c\u5e76\u5f55\u4e0b\u4f60\u7684\u8bb2\u89e3\u3002"
                    ),
                    "estimated_time": 10,
                }
            )
            plan["learning_methods"].append("feynman")

        for gap in gaps:
            plan["tasks"].append(
                {
                    "type": "review",
                    "skill": gap,
                    "instruction": (
                        f"\u590d\u4e60\u201c{gap}\u201d\uff0c\u5b8c\u62103\u9053\u5de9\u56fa\u9898\u3002"
                    ),
                    "estimated_time": 8,
                }
            )

        attribution = enrichment.get("error_attribution") or {}
        for tag in list(attribution.get("top_tags") or [])[:2]:
            plan["tasks"].append(
                {
                    "type": "error_correction",
                    "skill": tag,
                    "instruction": _error_correction_instruction(str(tag)),
                    "estimated_time": 8,
                }
            )
            plan["learning_methods"].append("error_correction")

        today = datetime.date.today()
        for skill in weak_skills:
            for index, day in enumerate(_REVIEW_INTERVALS):
                plan["review_schedule"].append(
                    {
                        "skill": skill,
                        "scheduled_date": (today + datetime.timedelta(days=day)).isoformat(),
                        "type": "spaced_repetition",
                        "session": index + 1,
                    }
                )

        for skill in weak_skills[:3]:
            plan["tasks"].append(
                {
                    "type": "socratic_dialogue",
                    "skill": skill,
                    "instruction": (
                        "\u4e0e\u82cf\u683c\u62c9\u5e95\u52a9\u6559\u8fdb\u884c\u4e00\u6b21\u5bf9\u8bdd\uff0c"
                        "\u56de\u7b54\u5f15\u5bfc\u6027\u95ee\u9898\u3002"
                    ),
                    "estimated_time": 15,
                }
            )
            plan["learning_methods"].append("socratic")

        plan["learning_methods"] = list(dict.fromkeys(plan["learning_methods"]))
        plan["estimated_total_hours"] = (
            sum(int(t.get("estimated_time", 0)) for t in plan["tasks"]) / 60.0
        )
        return plan

    @staticmethod
    def _scientific_markdown(scientific: dict[str, Any]) -> str:
        lines = [
            "",
            "",
            "## \u79d1\u5b66\u5b66\u4e60\u65b9\u6cd5",
            "",
        ]
        tasks = scientific.get("tasks") or []
        if tasks:
            lines.append("### \u4efb\u52a1")
            for task in tasks:
                lines.append(
                    f"- [{task.get('type')}] {task.get('skill')}: {task.get('instruction')}"
                )
            lines.append("")
        schedule = scientific.get("review_schedule") or []
        if schedule:
            lines.append("### \u95f4\u9694\u590d\u4e60")
            for row in schedule[:10]:
                lines.append(
                    f"- {row.get('scheduled_date')} · {row.get('skill')} "
                    f"(session {row.get('session')})"
                )
            if len(schedule) > 10:
                lines.append(f"- \u2026\u5171 {len(schedule)} \u4e2a\u590d\u4e60\u8282\u70b9")
            lines.append("")
        hours = scientific.get("estimated_total_hours") or 0
        lines.append(f"\u9884\u4f30\u603b\u7528\u65f6\uff1a{hours:.1f} \u5c0f\u65f6")
        if scientific.get("message"):
            lines.extend(["", f"- {scientific['message']}"])
        if scientific.get("recommendation"):
            lines.append(f"- {scientific['recommendation']}")
        style = scientific.get("learning_style")
        adaptation = scientific.get("style_adaptation") or {}
        if style or adaptation:
            lines.extend(["", "## \u5b66\u4e60\u98ce\u683c\u9002\u914d", ""])
            if style:
                lines.append(f"- \u63a8\u65ad\u98ce\u683c\uff1a{style}")
            suggestion = adaptation.get("suggestion")
            if suggestion:
                lines.append(f"- {suggestion}")
            materials = adaptation.get("material_type") or []
            if materials:
                lines.append("- \u63a8\u8350\u6750\u6599\uff1a" + ", ".join(materials))
        return "\n".join(lines)
