"""Planning agent — learning recommendations and practice-loop trigger."""

from __future__ import annotations

import datetime
from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
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
        scientific = self.generate_scientific_plan(
            ctx.diagnosis,
            ctx.profile,
            enrichment=enrichment if isinstance(enrichment, dict) else {},
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
        weak_skills = list(enrichment.get("weak_skills") or [])
        if not weak_skills:
            weak_skills = [
                row.knowledge_id
                for row in diagnosis.knowledge_mastery
                if row.level == "weak"
            ]
        gaps = list(enrichment.get("prerequisite_gaps") or [])

        plan: dict[str, Any] = {
            "tasks": [],
            "review_schedule": [],
            "learning_methods": [],
            "estimated_total_hours": 0.0,
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
        return "\n".join(lines)
