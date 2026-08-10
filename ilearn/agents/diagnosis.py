"""Diagnosis agent — learning-situation report and portrait updates."""

from __future__ import annotations

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.diagnosis import Diagnoser, PortraitUpdater
from ilearn.core.schemas import LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider

__all__ = ["DiagnosisAgent", "PortraitUpdater"]


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
        diagnosis = self._diagnoser.diagnose(ctx.profile, ctx.paper, ctx.grades)
        portrait = PortraitUpdater.update(
            ctx.portrait or LearnerPortrait(student_key=_student_key(ctx.profile)),
            ctx.grades,
            ctx.session_id,
            self._curriculum,
            grade=ctx.profile.grade,
        )
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={"diagnosis": diagnosis, "portrait": portrait},
        )
