"""State-machine orchestration for the ILearn multi-agent pipeline."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.planning import PlanningAgent
from ilearn.agents.practice import PracticeAgent, evidence_from_grades
from ilearn.core.evidence import append_evidence
from ilearn.agents.protocol import AgentContext
from ilearn.core.report import render_full_report
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    LearningPlanReport,
    SessionPhase,
    SessionState,
    StudentAnswer,
    StudentProfile,
)
from ilearn.providers.curriculum import CurriculumProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore


class MultiAgentOrchestrator:
    """Run ILearn agents and persist each state-machine transition."""

    def __init__(
        self,
        store: SessionStore,
        curriculum: CurriculumProvider,
        llm: LLMClient | None = None,
    ) -> None:
        self._store = store
        pilot_dir = getattr(
            curriculum,
            "_data_dir",
            Path(__file__).resolve().parents[2] / "data" / "pilot",
        )
        self._curriculum_agent = CurriculumAgent(pilot_dir=Path(pilot_dir))
        self._assessment = AssessmentAgent(curriculum)
        self._practice = PracticeAgent(llm)
        self._diagnosis = DiagnosisAgent(curriculum)
        self._planning = PlanningAgent(curriculum)

    @staticmethod
    def _ctx(
        session: SessionState,
        *,
        phase: SessionPhase | None = None,
        metadata: dict | None = None,
    ) -> AgentContext:
        return AgentContext(
            session_id=session.session_id,
            phase=phase or session.phase,
            profile=session.profile,
            paper=session.paper,
            answers=list(session.answers),
            image_answers=list(session.image_answers),
            grades=list(session.grades),
            diagnosis=session.diagnosis,
            plan=session.plan,
            portrait=session.portrait,
            loop_count=session.loop_count,
            evidence_log=list(session.evidence_log),
            metadata=metadata or {},
        )

    def create_session(self, profile: StudentProfile) -> str:
        return self._store.create(profile).session_id

    def current_phase(self, session_id: str) -> SessionPhase:
        return self._store.load(session_id).phase

    def generate_assessment(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        citation_result = self._curriculum_agent.run(self._ctx(session))
        session.curriculum_citations = citation_result.payload["citations"]

        result = self._assessment.run(
            self._ctx(session, phase=SessionPhase.ASSESS)
        )
        session.paper = result.payload["paper"]
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.diagnosis = None
        session.plan = None
        session.phase = result.phase
        self._store.save(session)
        return session.paper

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
            StudentAnswer(item_id=item.id, answer_text=answers.get(item.id, ""))
            for item in paper.items
        ]
        session.grades = []
        session.diagnosis = None
        session.plan = None
        session.phase = SessionPhase.GRADE
        return self._store.save(session)

    def grade(self, session_id: str) -> list[GradeResult]:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        answer_map = {answer.item_id: answer.answer_text for answer in session.answers}
        session.answers = [
            StudentAnswer(item_id=item.id, answer_text=answer_map.get(item.id, ""))
            for item in paper.items
        ]
        result = self._practice.run(
            self._ctx(session, phase=SessionPhase.GRADE)
        )
        session.grades = result.payload["grades"]
        for event in result.payload.get("evidence") or evidence_from_grades(
            session.session_id, session.grades
        ):
            append_evidence(session, event)
        session.diagnosis = None
        session.plan = None
        session.phase = result.phase
        self._store.save(session)
        return session.grades

    def diagnose(self, session_id: str) -> DiagnosisReport:
        session = self._store.load(session_id)
        self._require_paper(session)
        if not session.grades:
            raise ValueError("session must be graded before diagnosis")
        result = self._diagnosis.run(
            self._ctx(session, phase=SessionPhase.DIAGNOSE)
        )
        session.diagnosis = result.payload["diagnosis"]
        session.portrait = result.payload["portrait"]
        session.plan = None
        session.phase = result.phase
        self._store.save(session)
        return session.diagnosis

    def plan(self, session_id: str) -> LearningPlanReport:
        session = self._store.load(session_id)
        if session.diagnosis is None:
            raise ValueError("session must be diagnosed before planning")
        result = self._planning.run(
            self._ctx(
                session,
                phase=SessionPhase.PLAN,
                metadata={"citations": list(session.curriculum_citations)},
            )
        )
        session.plan = result.payload["plan"]
        session.phase = result.phase
        self._store.save(session)
        return session.plan

    def run_after_submit(self, session_id: str) -> SessionState:
        self.grade(session_id)
        self.diagnose(session_id)
        self.plan(session_id)
        session = self._store.load(session_id)
        if session.phase == SessionPhase.PRACTICE_LOOP:
            self.start_practice_loop(session_id)
        return self._store.load(session_id)

    def start_practice_loop(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        if session.diagnosis is None:
            raise ValueError("session must be diagnosed before starting practice loop")
        weak_ids = [
            mastery.knowledge_id
            for mastery in session.diagnosis.knowledge_mastery
            if mastery.level == "weak"
        ][:5]
        if not weak_ids:
            raise ValueError("practice loop requires weak knowledge ids")

        result = self._assessment.run(
            self._ctx(
                session,
                phase=SessionPhase.PRACTICE_LOOP,
                metadata={
                    "paper_type": "followup",
                    "weak_knowledge_ids": weak_ids,
                },
            )
        )
        session.paper = result.payload["paper"]
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.loop_count += 1
        session.phase = result.phase
        self._store.save(session)
        return session.paper

    def report(self, session_id: str) -> str:
        return render_full_report(self._store.load(session_id))

    @staticmethod
    def _require_paper(session: SessionState) -> AssessmentPaper:
        if session.paper is None:
            raise ValueError("session must have an assessment paper")
        return session.paper
