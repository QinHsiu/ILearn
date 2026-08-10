"""Learning plan generation from diagnosis results."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ilearn.core.review import due_knowledge_ids
from ilearn.core.replan import replan_adjustments, should_replan
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    LearnerPortrait,
    LearningPlanReport,
    PlanDay,
    StudentProfile,
)
from ilearn.providers.curriculum import CurriculumProvider, PilotBeijingRenjiaoProvider

_DEFAULT_PLAN_DAYS = 7
_MAX_PLAN_DAYS = 14
_DEFAULT_DAILY_MINUTES = 40


def _default_pilot_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "pilot"


class Planner:
    """Build a structured 1–2 week learning plan from diagnosis."""

    def __init__(self, curriculum: CurriculumProvider | None = None) -> None:
        self._curriculum = curriculum or PilotBeijingRenjiaoProvider(_default_pilot_dir())

    def plan(
        self,
        profile: StudentProfile,
        diagnosis: DiagnosisReport,
        daily_minutes: int = _DEFAULT_DAILY_MINUTES,
        plan_days: int = _DEFAULT_PLAN_DAYS,
        portrait: LearnerPortrait | None = None,
        today: date | None = None,
    ) -> LearningPlanReport:
        plan_days = min(max(1, plan_days), _MAX_PLAN_DAYS)
        knowledge_by_id = {
            node.id: node for node in self._curriculum.list_knowledge(profile.grade)
        }

        replan = portrait is not None and should_replan(portrait, diagnosis)
        focus_order = self._focus_knowledge_order(diagnosis, easier_first=replan)
        review_ids = (
            due_knowledge_ids(portrait, today or date.today())
            if portrait is not None
            else []
        )
        goal = (
            f"在{plan_days}天内巩固{profile.grade}年级数学薄弱知识点，"
            "提升测评正确率与解题稳定性"
        )
        milestones = self._build_milestones(plan_days, focus_order, knowledge_by_id)
        days = self._build_days(
            plan_days,
            focus_order,
            knowledge_by_id,
            daily_minutes,
            review_ids=review_ids,
            replan=replan,
            diagnosis=diagnosis,
        )
        markdown = self._render_plan_markdown(
            profile, diagnosis, goal, milestones, days, daily_minutes
        )

        return LearningPlanReport(
            goal=goal,
            milestones=milestones,
            days=days,
            markdown=markdown,
        )

    def _focus_knowledge_order(
        self, diagnosis: DiagnosisReport, *, easier_first: bool = False
    ) -> list[str]:
        mastery_by_id = {km.knowledge_id: km for km in diagnosis.knowledge_mastery}
        if diagnosis.interventions:
            ordered = [
                item.knowledge_id
                for item in sorted(diagnosis.interventions, key=lambda x: x.priority)
            ]
            if easier_first:
                return sorted(
                    ordered,
                    key=lambda kid: mastery_by_id.get(
                        kid,
                        KnowledgeMastery(knowledge_id=kid, score_rate=0.0, level="weak"),
                    ).score_rate,
                    reverse=True,
                )
            return ordered
        weak = [
            km.knowledge_id
            for km in sorted(
                (km for km in diagnosis.knowledge_mastery if km.level != "mastered"),
                key=lambda km: (km.score_rate, km.knowledge_id),
            )
        ]
        if easier_first and weak:
            return sorted(
                weak,
                key=lambda kid: mastery_by_id.get(
                    kid,
                    KnowledgeMastery(knowledge_id=kid, score_rate=0.0, level="weak"),
                ).score_rate,
                reverse=True,
            )
        return weak

    def _build_milestones(
        self,
        plan_days: int,
        focus_order: list[str],
        knowledge_by_id: dict[str, object],
    ) -> list[str]:
        milestones: list[str] = []
        if not focus_order:
            milestones.append("保持已掌握内容的定期复习与自测")
            return milestones

        first_name = self._knowledge_name(focus_order[0], knowledge_by_id)
        milestones.append(f"第1–2天：重点突破「{first_name}」")
        if len(focus_order) > 1:
            second_name = self._knowledge_name(focus_order[1], knowledge_by_id)
            milestones.append(f"第3–5天：巩固「{second_name}」及相关变式")
        milestones.append(
            f"第{max(3, plan_days - 1)}–{plan_days}天：综合练习与错题回顾"
        )
        return milestones

    def _build_days(
        self,
        plan_days: int,
        focus_order: list[str],
        knowledge_by_id: dict[str, object],
        daily_minutes: int,
        *,
        review_ids: list[str] | None = None,
        replan: bool = False,
        diagnosis: DiagnosisReport | None = None,
    ) -> list[PlanDay]:
        review_ids = review_ids or []
        confidence_task = (
            replan_adjustments(diagnosis).get("confidence_task")
            if replan and diagnosis is not None
            else None
        )
        days: list[PlanDay] = []
        for day_num in range(1, plan_days + 1):
            if focus_order:
                knowledge_id = focus_order[(day_num - 1) % len(focus_order)]
                focus_ids = [knowledge_id]
                tasks = self._day_tasks(knowledge_id, knowledge_by_id, day_num)
            else:
                focus_ids = []
                tasks = ["复习已掌握内容，完成5道同年级综合题并核对答案"]
            if confidence_task and day_num == 1:
                tasks = [confidence_task] + tasks
            if review_ids and day_num == 1:
                review_tasks = [
                    f"复习「{self._knowledge_name(kid, knowledge_by_id)}」（间隔复习）"
                    for kid in review_ids
                ]
                tasks = review_tasks + tasks
                focus_ids = list(dict.fromkeys(review_ids + focus_ids))
            days.append(
                PlanDay(
                    day=day_num,
                    focus_knowledge_ids=focus_ids,
                    tasks=tasks,
                    minutes=daily_minutes,
                )
            )
        return days

    @staticmethod
    def _knowledge_name(knowledge_id: str, knowledge_by_id: dict[str, object]) -> str:
        node = knowledge_by_id.get(knowledge_id)
        return node.name if node is not None else knowledge_id

    def _day_tasks(
        self,
        knowledge_id: str,
        knowledge_by_id: dict[str, object],
        day_num: int,
    ) -> list[str]:
        name = self._knowledge_name(knowledge_id, knowledge_by_id)
        if day_num == 1:
            return [
                f"复习「{name}」核心概念与例题",
                f"完成3道「{name}」基础练习并订正",
                "记录仍不确定的步骤或疑问",
            ]
        if day_num % 2 == 0:
            return [
                f"继续练习「{name}」中等难度题目",
                "对照评分标准检查解题步骤是否完整",
            ]
        return [
            f"针对「{name}」做错题回顾",
            "完成1套小型自测并统计正确率",
        ]

    def _render_plan_markdown(
        self,
        profile: StudentProfile,
        diagnosis: DiagnosisReport,
        goal: str,
        milestones: list[str],
        days: list[PlanDay],
        daily_minutes: int,
    ) -> str:
        lines = [
            "# 学习计划",
            "",
            f"**适用年级：** {profile.grade}年级  ",
            f"**课标：** {diagnosis.curriculum_label}  ",
            f"**建议每日学习：** {daily_minutes} 分钟",
            "",
            "## 目标",
            "",
            goal,
            "",
            "## 里程碑",
            "",
        ]
        for milestone in milestones:
            lines.append(f"- {milestone}")
        lines.extend(["", "## 每日安排", ""])
        for day in days:
            focus_text = "、".join(day.focus_knowledge_ids) or "综合复习"
            lines.append(f"### 第 {day.day} 天（约 {day.minutes} 分钟）")
            lines.append(f"- **重点：** {focus_text}")
            for task in day.tasks:
                lines.append(f"- {task}")
            lines.append("")
        lines.append(
            "> 本计划为智能助手建议，不能替代教师专业评价。"
        )
        return "\n".join(lines).strip()
