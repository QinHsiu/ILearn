"""State-machine orchestration for the ILearn multi-agent pipeline."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent, bind_source_refs_to_item
from ilearn.agents.capabilities import assert_writes_allowed
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.planning import PlanningAgent
from ilearn.agents.practice import PracticeAgent, evidence_from_grades
from ilearn.agents.tutor import TutorAgent
from ilearn.core.context_budget import trim_context
from ilearn.core.item_validators import revise_paper_once, validate_paper as validate_item_paper
from ilearn.core.evidence import append_evidence
from ilearn.agents.protocol import AgentContext
from ilearn.core.quality_gate import (
    degraded_assessment_result,
    degraded_diagnosis_result,
    degraded_plan_result,
    run_with_quality_gate,
    valid_assessment_result,
    valid_diagnosis_result,
    valid_plan_result,
)
from ilearn.core.report import render_full_report
from ilearn.core.schemas import (
    AgentDecision,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    LearningPlanReport,
    PendingQuestion,
    SessionPhase,
    SessionState,
    StudentAnswer,
    StudentProfile,
    TutorTurn,
)
from ilearn.providers.curriculum import CurriculumProvider, load_example_bank
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
        self._curriculum = curriculum
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
        self._tutor = TutorAgent()

    @staticmethod
    def _ctx(
        session: SessionState,
        *,
        phase: SessionPhase | None = None,
        metadata: dict | None = None,
    ) -> AgentContext:
        context_metadata = dict(session.metadata)
        context_metadata.update(metadata or {})
        return trim_context(
            deepcopy(
                AgentContext(
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
                    metadata=context_metadata,
                )
            )
        )

    def create_session(self, profile: StudentProfile) -> str:
        return self._store.create(profile).session_id

    @staticmethod
    def _record_decision(
        session: SessionState,
        agent: str,
        phase: SessionPhase,
        reason: str,
        *,
        ok: bool = True,
        degraded: bool = False,
        evidence_ids: list[str] | None = None,
    ) -> None:
        session.decision_log.append(
            AgentDecision(
                agent=agent,
                phase=phase,
                reason=reason,
                evidence_ids=evidence_ids or [],
                ok=ok,
                degraded=degraded,
            )
        )

    def current_phase(self, session_id: str) -> SessionPhase:
        return self._store.load(session_id).phase

    @staticmethod
    def _bind_pending_questions(
        session: SessionState,
        paper: AssessmentPaper,
    ) -> None:
        session.pending_questions = [
            PendingQuestion(
                question_id=item.id,
                expected_answer=item.answer_key or "",
                paper_id=session.session_id,
            )
            for item in paper.items
        ]

    def _validate_and_revise_paper(
        self,
        session: SessionState,
        paper: AssessmentPaper,
    ) -> tuple[AssessmentPaper, str]:
        issues = validate_item_paper(paper, grade=session.profile.grade)
        revised_paper = revise_paper_once(
            paper,
            issues,
            profile=session.profile,
            curriculum=self._curriculum,
        )
        revised = revised_paper.items != paper.items
        if revised:
            pilot_dir = getattr(
                self._curriculum,
                "_data_dir",
                Path(__file__).resolve().parents[2] / "data" / "pilot",
            )
            example_bank = load_example_bank(Path(pilot_dir))
            for item in revised_paper.items:
                item.source_refs = bind_source_refs_to_item(
                    item,
                    list(session.curriculum_citations),
                    example_bank,
                )
        remaining_issues = validate_item_paper(
            revised_paper, grade=session.profile.grade
        )
        if revised:
            revision_summary = "revised once"
        elif issues:
            revision_summary = "revision no-op"
        else:
            revision_summary = "all clear"
        summary = (
            f"validated paper: {len(issues)} issue(s), {revision_summary}; "
            f"remaining {len(remaining_issues)} issue(s)"
        )
        return revised_paper, summary

    def generate_assessment(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        citation_result = self._curriculum_agent.run(self._ctx(session))
        assert_writes_allowed(
            self._curriculum_agent.name,
            set(citation_result.payload) & {"citations"},
        )
        session.curriculum_citations = citation_result.payload["citations"]

        result, degraded = run_with_quality_gate(
            lambda: self._assessment.run(
                self._ctx(session, phase=SessionPhase.ASSESS)
            ),
            valid_assessment_result,
        )
        if degraded:
            result = degraded_assessment_result(session.profile)
            validator_summary: str | None = None
        else:
            paper, validator_summary = self._validate_and_revise_paper(
                session, result.payload["paper"]
            )
            result.payload["paper"] = paper
        assert_writes_allowed(
            self._assessment.name,
            set(result.payload) & {"paper"},
        )
        session.paper = result.payload["paper"]
        self._bind_pending_questions(session, session.paper)
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.diagnosis = None
        session.plan = None
        session.phase = result.phase
        self._record_decision(
            session,
            self._assessment.name,
            SessionPhase.ASSESS,
            "assessment generated",
            ok=not degraded,
            degraded=degraded,
        )
        if validator_summary is not None:
            self._record_decision(
                session,
                "item_validators",
                SessionPhase.ASSESS,
                validator_summary,
                ok=True,
            )
        self._store.save(session)
        return session.paper

    def submit(
        self,
        session_id: str,
        answers: dict[str, str],
        *,
        item_meta: dict[str, dict] | None = None,
    ) -> SessionState:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        if session.pending_questions:
            known_ids = {
                question.question_id for question in session.pending_questions
            }
        else:
            known_ids = {item.id for item in paper.items}
        unknown_ids = set(answers) - known_ids
        if unknown_ids:
            unknown = ", ".join(sorted(unknown_ids))
            raise ValueError(f"answers contain unknown item ids: {unknown}")

        session.answers = [
            StudentAnswer(item_id=item.id, answer_text=answers.get(item.id, ""))
            for item in paper.items
        ]
        session.metadata["item_meta"] = item_meta or {}
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
        assert_writes_allowed(
            self._practice.name,
            set(result.payload) & {"grades", "evidence"},
        )
        session.grades = result.payload["grades"]
        evidence_events = result.payload.get("evidence") or evidence_from_grades(
            session.session_id, session.grades
        )
        for event in evidence_events:
            append_evidence(session, event)
        session.diagnosis = None
        session.plan = None
        session.phase = result.phase
        self._record_decision(
            session,
            self._practice.name,
            SessionPhase.GRADE,
            "answers graded",
            evidence_ids=[event.evidence_id for event in evidence_events],
        )
        self._store.save(session)
        return session.grades

    def diagnose(self, session_id: str) -> DiagnosisReport:
        session = self._store.load(session_id)
        self._require_paper(session)
        if not session.grades:
            raise ValueError("session must be graded before diagnosis")
        result, degraded = run_with_quality_gate(
            lambda: self._diagnosis.run(
                self._ctx(session, phase=SessionPhase.DIAGNOSE)
            ),
            valid_diagnosis_result,
        )
        if degraded:
            result = degraded_diagnosis_result(
                session.profile,
                self._require_paper(session).curriculum_label,
                session.portrait,
            )
        assert_writes_allowed(
            self._diagnosis.name,
            set(result.payload) & {"diagnosis", "portrait"},
        )
        session.diagnosis = result.payload["diagnosis"]
        session.portrait = result.payload["portrait"]
        session.plan = None
        session.phase = result.phase
        self._record_decision(
            session,
            self._diagnosis.name,
            SessionPhase.DIAGNOSE,
            "diagnosis completed",
            ok=not degraded,
            degraded=degraded,
        )
        self._store.save(session)
        return session.diagnosis

    def plan(self, session_id: str) -> LearningPlanReport:
        session = self._store.load(session_id)
        if session.diagnosis is None:
            raise ValueError("session must be diagnosed before planning")
        result, degraded = run_with_quality_gate(
            lambda: self._planning.run(
                self._ctx(
                    session,
                    phase=SessionPhase.PLAN,
                    metadata={"citations": list(session.curriculum_citations)},
                )
            ),
            valid_plan_result,
        )
        if degraded:
            result = degraded_plan_result()
        assert_writes_allowed(
            self._planning.name,
            set(result.payload) & {"plan", "plan_history_append"},
        )
        session.plan = result.payload["plan"]
        for entry in result.payload.get("plan_history_append", []):
            session.plan_history.append(entry)
        session.phase = result.phase
        self._record_decision(
            session,
            self._planning.name,
            SessionPhase.PLAN,
            "learning plan created",
            ok=not degraded,
            degraded=degraded,
        )
        self._store.save(session)
        return session.plan

    def request_replan(self, session_id: str) -> LearningPlanReport:
        """Re-run planning with current portrait/diagnosis; supersede prior plan."""
        session = self._store.load(session_id)
        if session.diagnosis is None:
            raise ValueError("session must be diagnosed before replanning")
        result = self._planning.run(
            self._ctx(
                session,
                phase=SessionPhase.PLAN,
                metadata={"citations": list(session.curriculum_citations)},
            )
        )
        assert_writes_allowed(
            self._planning.name,
            set(result.payload) & {"plan", "plan_history_append"},
        )
        session.plan = result.payload["plan"]
        for entry in result.payload.get("plan_history_append", []):
            session.plan_history.append(entry)
        session.phase = result.phase
        self._record_decision(
            session,
            self._planning.name,
            SessionPhase.PLAN,
            "learning plan revised",
        )
        self._store.save(session)
        return session.plan

    def tutor_start(self, session_id: str, item_id: str) -> TutorTurn:
        """Begin Socratic tutoring for a graded item."""
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        item = next((i for i in paper.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item id: {item_id}")
        grade = next((g for g in session.grades if g.item_id == item_id), None)
        error_tag = grade.error_tags[0] if grade and grade.error_tags else None
        turn = self._tutor.start(item, error_tag)
        session.tutor_by_item[item_id] = turn
        self._record_decision(
            session,
            self._tutor.name,
            SessionPhase.PRACTICE,
            "tutoring started",
        )
        self._store.save(session)
        return turn

    def tutor_step(
        self, session_id: str, item_id: str, user_message: str
    ) -> TutorTurn:
        session = self._store.load(session_id)
        paper = self._require_paper(session)
        item = next((row for row in paper.items if row.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item id: {item_id}")
        previous = session.tutor_by_item.get(item_id)
        if previous is None:
            raise ValueError("tutoring has not started for this item")
        turn = self._tutor.step(previous.phase, user_message, item)
        session.tutor_by_item[item_id] = turn
        self._record_decision(
            session,
            self._tutor.name,
            SessionPhase.PRACTICE,
            "tutoring hint",
        )
        self._store.save(session)
        return turn

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
        assert_writes_allowed(
            self._assessment.name,
            set(result.payload) & {"paper"},
        )
        session.paper, validator_summary = self._validate_and_revise_paper(
            session, result.payload["paper"]
        )
        self._record_decision(
            session,
            "item_validators",
            SessionPhase.PRACTICE_LOOP,
            validator_summary,
        )
        self._bind_pending_questions(session, session.paper)
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
