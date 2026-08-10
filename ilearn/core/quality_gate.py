"""Retry and deterministic degradation for agent quality checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ilearn.agents.protocol import AgentResult
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    LearnerPortrait,
    LearningPlanReport,
    SessionPhase,
    StudentProfile,
)

T = TypeVar("T")


def run_with_quality_gate(
    run_once: Callable[[], T],
    validate: Callable[[T], bool],
    *,
    max_retries: int = 1,
) -> tuple[T, bool]:
    """Run an operation until valid or its retry budget is exhausted."""
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    for _ in range(max_retries + 1):
        result = run_once()
        if validate(result):
            return result, False
    return result, True


def valid_assessment_result(result: AgentResult) -> bool:
    paper = result.payload.get("paper")
    return isinstance(paper, AssessmentPaper) and len(paper.items) >= 1


def valid_diagnosis_result(result: AgentResult) -> bool:
    diagnosis = result.payload.get("diagnosis")
    return isinstance(diagnosis, DiagnosisReport) and bool(
        diagnosis.knowledge_mastery or diagnosis.interventions
    )


def valid_plan_result(result: AgentResult) -> bool:
    plan = result.payload.get("plan")
    return isinstance(plan, LearningPlanReport) and bool(
        plan.markdown.strip() or any(day.tasks for day in plan.days)
    )


def degraded_assessment_result(profile: StudentProfile) -> AgentResult:
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="quality-gate-fallback",
                stem="暂时无法生成完整测评，请稍后重试。",
                type="fill",
                difficulty="easy",
                knowledge_ids=[],
                answer_key="",
            )
        ],
        grade=profile.grade,
        curriculum_label="质量门降级结果",
        paper_version="degraded",
    )
    return AgentResult(
        phase=SessionPhase.PRACTICE,
        payload={"paper": paper, "degraded": True},
    )


def degraded_diagnosis_result(
    profile: StudentProfile,
    curriculum_label: str,
    portrait: LearnerPortrait | None = None,
) -> AgentResult:
    student_key = profile.region.strip().casefold().replace(" ", "_")
    return AgentResult(
        phase=SessionPhase.PLAN,
        payload={
            "diagnosis": DiagnosisReport(
                curriculum_label=curriculum_label,
                flags=["quality_gate_degraded"],
            ),
            "portrait": portrait
            or LearnerPortrait(student_key=f"{student_key}_g{profile.grade}"),
            "degraded": True,
        },
    )


def degraded_plan_result() -> AgentResult:
    return AgentResult(
        phase=SessionPhase.PLAN,
        payload={
            "plan": LearningPlanReport(
                goal="等待生成个性化学习计划",
                markdown="学习计划生成质量不足，请稍后重试。",
            ),
            "plan_history_append": [],
            "degraded": True,
        },
    )
