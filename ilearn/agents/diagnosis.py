"""Diagnosis agent — learning-situation report and portrait updates."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.diagnosis import Diagnoser, PortraitDimensionUpdater, PortraitUpdater
from ilearn.core.schemas import LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider

__all__ = ["DiagnosisAgent", "PortraitDimensionUpdater", "PortraitUpdater"]


def _student_key(profile: StudentProfile) -> str:
    region = profile.region.strip().casefold().replace(" ", "_")
    return f"{region}_g{profile.grade}"


class DiagnosisAgent:
    name = "diagnosis"

    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._curriculum = curriculum
        self._diagnoser = Diagnoser(curriculum)

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("DiagnosisAgent requires paper in context")
        evidence = list(ctx.evidence_log)
        portrait = ctx.portrait or LearnerPortrait(student_key=_student_key(ctx.profile))
        portrait = PortraitUpdater.update(
            portrait,
            ctx.grades,
            ctx.session_id,
            self._curriculum,
            grade=ctx.profile.grade,
            evidence=evidence or None,
        )
        diagnosis = self._diagnoser.diagnose(
            ctx.profile,
            ctx.paper,
            ctx.grades,
            portrait=portrait,
            evidence=evidence or None,
        )
        if evidence:
            portrait = PortraitDimensionUpdater.apply_from_evidence(portrait, evidence)
        else:
            portrait = PortraitDimensionUpdater.apply(
                portrait, ctx.grades, profile=ctx.profile
            )
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={"diagnosis": diagnosis, "portrait": portrait},
        )
