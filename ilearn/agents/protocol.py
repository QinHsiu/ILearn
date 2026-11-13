from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from typing import TYPE_CHECKING

from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    ImageAnswer,
    KnowledgeEvidence,
    LearnerPortrait,
    LearningPlanReport,
    SessionPhase,
    StudentAnswer,
    StudentProfile,
)

if TYPE_CHECKING:
    from ilearn.core.learner_state import LearnerState

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
    evidence_log: list[KnowledgeEvidence] = field(default_factory=list)
    hint_interactions: dict | None = None
    metadata: dict = field(default_factory=dict)
    learner_state: "LearnerState | None" = None


@dataclass
class AgentResult:
    phase: SessionPhase
    payload: dict = field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    name: str

    def run(self, ctx: AgentContext) -> AgentResult: ...
