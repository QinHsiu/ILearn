"""Planning agent — learning recommendations and practice-loop trigger."""

from __future__ import annotations

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
            plan.markdown += "\n\n## 课标依据\n" + "\n".join(
                f"- {c.title}：{c.excerpt}" for c in citations[:3]
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
            },
        )
