"""Backward-compatible facade for multi-agent orchestration."""

from __future__ import annotations

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    LearningPlanReport,
    SessionPhase,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import CurriculumProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore


class Orchestrator:
    """Preserve the original API while delegating to the agent state machine."""

    def __init__(
        self,
        store: SessionStore,
        curriculum: CurriculumProvider,
        llm: LLMClient | None = None,
    ) -> None:
        self._inner = MultiAgentOrchestrator(store, curriculum, llm)

    def create_session(self, profile: StudentProfile) -> str:
        return self._inner.create_session(profile)

    def generate_assessment(self, session_id: str) -> AssessmentPaper:
        return self._inner.generate_assessment(session_id)

    def submit(
        self,
        session_id: str,
        answers: dict[str, str],
    ) -> SessionState:
        return self._inner.submit(session_id, answers)

    def grade(self, session_id: str) -> list[GradeResult]:
        return self._inner.grade(session_id)

    def diagnose(self, session_id: str) -> DiagnosisReport:
        return self._inner.diagnose(session_id)

    def plan(self, session_id: str) -> LearningPlanReport:
        return self._inner.plan(session_id)

    def run_after_submit(self, session_id: str) -> SessionState:
        return self._inner.run_after_submit(session_id)

    def report(self, session_id: str) -> str:
        return self._inner.report(session_id)

    def start_practice_loop(self, session_id: str) -> AssessmentPaper:
        return self._inner.start_practice_loop(session_id)

    def current_phase(self, session_id: str) -> SessionPhase:
        return self._inner.current_phase(session_id)
