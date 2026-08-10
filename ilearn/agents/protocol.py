from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    ImageAnswer,
    LearnerPortrait,
    LearningPlanReport,
    SessionPhase,
    StudentAnswer,
    StudentProfile,
)

__all__ = ["Agent", "AgentContext", "AgentResult", "SessionPhase"]


@dataclass
class AgentContext:
    session_id: str
    phase: SessionPhase
    profile: StudentProfile
    paper: AssessmentPaper | None = None
    answers: list[StudentAnswer] = field(default_factory=list)
    image_answers: list[ImageAnswer] = field(default_factory=list)
    grades: list[GradeResult] = field(default_factory=list)
    diagnosis: DiagnosisReport | None = None
    plan: LearningPlanReport | None = None
    portrait: LearnerPortrait | None = None
    loop_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    phase: SessionPhase
    payload: dict = field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    name: str

    def run(self, ctx: AgentContext) -> AgentResult: ...
