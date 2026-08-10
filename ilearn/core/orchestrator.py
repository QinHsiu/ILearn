"""Thin orchestration layer for the ILearn assessment pipeline."""

from __future__ import annotations

from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.diagnosis import Diagnoser
from ilearn.core.grading import StepGrader
from ilearn.core.planning import Planner
from ilearn.core.report import render_full_report
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    LearningPlanReport,
    SessionState,
    StudentAnswer,
    StudentProfile,
)
from ilearn.providers.curriculum import CurriculumProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore


class Orchestrator:
    """Sequence existing pipeline components and persist each result."""

    def __init__(
        self,
        store: SessionStore,
        curriculum: CurriculumProvider,
        llm: LLMClient | None = None,
    ) -> None:
        self._store = store
        self._assessment_builder = AssessmentBuilder(curriculum)
        self._grader = StepGrader(llm)
        self._diagnoser = Diagnoser(curriculum)
        self._planner = Planner(curriculum)

    def create_session(self, profile: StudentProfile) -> str:
        return self._store.create(profile).session_id

    def generate_assessment(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        paper = self._assessment_builder.build(session.profile)
        session.paper = paper
        session.answers = []
        session.grades = []
        session.diagnosis = None
        session.plan = None
        self._store.save(session)
        return paper

    def submit(
        self,
        session_id: str,
        answers: dict[str, str],
    ) -> SessionState:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        known_ids = {item.id for item in paper.items}
        unknown_ids = set(answers) - known_ids
        if unknown_ids:
            unknown = ", ".join(sorted(unknown_ids))
            raise ValueError(f"answers contain unknown item ids: {unknown}")

        session.answers = [
            StudentAnswer(item_id=item.id, answer_text=answers[item.id])
            for item in paper.items
            if item.id in answers
        ]
        session.grades = []
        session.diagnosis = None
        session.plan = None
        return self._store.save(session)

    def grade(self, session_id: str) -> list[GradeResult]:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        session.grades = self._grader.grade_paper(paper, session.answers)
        session.diagnosis = None
        session.plan = None
        self._store.save(session)
        return session.grades

    def diagnose(self, session_id: str) -> DiagnosisReport:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        if not session.grades:
            raise ValueError("session must be graded before diagnosis")
        session.diagnosis = self._diagnoser.diagnose(
            session.profile,
            paper,
            session.grades,
        )
        session.plan = None
        self._store.save(session)
        return session.diagnosis

    def plan(self, session_id: str) -> LearningPlanReport:
        session = self._store.load(session_id)
        if session.diagnosis is None:
            raise ValueError("session must be diagnosed before planning")
        session.plan = self._planner.plan(session.profile, session.diagnosis)
        self._store.save(session)
        return session.plan

    def run_after_submit(self, session_id: str) -> SessionState:
        self.grade(session_id)
        self.diagnose(session_id)
        self.plan(session_id)
        return self._store.load(session_id)

    def report(self, session_id: str) -> str:
        return render_full_report(self._store.load(session_id))

    @staticmethod
    def _require_paper(session: SessionState) -> AssessmentPaper:
        if session.paper is None:
            raise ValueError("session must have an assessment paper")
        return session.paper
