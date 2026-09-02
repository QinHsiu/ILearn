"""State-machine orchestration for the ILearn multi-agent pipeline."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent, bind_source_refs_to_item
from ilearn.agents.capabilities import assert_writes_allowed
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.guard import SAFE_FALLBACK, GuardAgent
from ilearn.agents.planning import PlanningAgent
from ilearn.agents.practice import PracticeAgent, evidence_from_grades
from ilearn.agents.tutor import TutorAgent
from ilearn.core.context_budget import trim_context
from ilearn.core.datetime_utils import utc_now
from ilearn.core.item_validators import revise_paper, validate_paper as validate_item_paper
from ilearn.core.assessment_timeout import (
    apply_submit_timeout,
    is_assessment_timed_out,
    mark_assessment_started,
)
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
from ilearn.core.phase_guard import PhaseGuard
from ilearn.core.session_paper import paper_for_tutor
from ilearn.core.report import render_full_report
from ilearn.core.session_lock import with_session_lock
from ilearn.core.schemas import (
    MAX_HINTS_PER_ITEM,
    AgentDecision,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    HintInteraction,
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
        tutor: TutorAgent | None = None,
    ) -> None:
        self._store = store
        self._curriculum = curriculum
        pilot_dir = getattr(
            curriculum,
            "_data_dir",
            Path(__file__).resolve().parents[2] / "data" / "pilot",
        )
        self._curriculum_agent = CurriculumAgent(pilot_dir=Path(pilot_dir))
        self._assessment = AssessmentAgent(curriculum, llm=llm)
        self._practice = PracticeAgent(llm)
        self._diagnosis = DiagnosisAgent(curriculum)
        self._planning = PlanningAgent(curriculum)
        self._tutor = tutor or TutorAgent()
        self._guard = GuardAgent()

    @staticmethod
    def _ctx(
        session: SessionState,
        *,
        phase: SessionPhase | None = None,
        metadata: dict | None = None,
    ) -> AgentContext:
        context_metadata = dict(session.metadata)
        context_metadata.update(metadata or {})
        if session.hint_interactions:
            context_metadata["hint_interactions"] = {
                item_id: [row.model_dump(mode="json") for row in rows]
                for item_id, rows in session.hint_interactions.items()
            }
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

    @with_session_lock
    def get_session(self, session_id: str) -> SessionState:
        return self._store.load(session_id)

    @with_session_lock
    def heartbeat(self, session_id: str) -> dict:
        session = self._store.load(session_id)
        session.metadata["last_heartbeat"] = utc_now().isoformat()
        self._store.save(session)
        return {
            "ok": True,
            "phase": session.phase.value if hasattr(session.phase, "value") else str(session.phase),
            "server_time": utc_now().isoformat(),
        }

    @staticmethod
    def _set_phase(session: SessionState, target: SessionPhase) -> None:
        PhaseGuard.transition(session, target)

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

    @with_session_lock
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
        result = revise_paper(
            paper,
            issues,
            profile=session.profile,
            curriculum=self._curriculum,
        )
        revised_paper = result.paper
        revised = revised_paper.items != paper.items or result.fallback_used
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
        if result.fallback_used:
            revision_summary = f"revised {result.attempts}, fallback"
        elif result.attempts:
            revision_summary = f"revised {result.attempts}"
        elif issues:
            revision_summary = "revision no-op"
        else:
            revision_summary = "all clear"
        summary = (
            f"validated paper: {len(issues)} issue(s), {revision_summary}; "
            f"remaining {len(remaining_issues)} issue(s)"
        )
        return revised_paper, summary

    @with_session_lock
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
        mark_assessment_started(session)
        self._set_phase(session, result.phase)
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

    @staticmethod
    def _adaptive_paper_dump(paper: AssessmentPaper) -> dict:
        return paper.model_dump(mode="json")

    @with_session_lock
    def start_adaptive_assessment(
        self,
        session_id: str,
        semester: str | None = None,
    ) -> dict:
        """Generate anchor paper for cold-start; does not replace session.paper."""
        session = self._store.load(session_id)
        payload = self._assessment.generate_adaptive_assessment(
            session.profile,
            is_first_time=True,
            semester=semester,
            portrait=session.portrait,
        )
        paper: AssessmentPaper = payload["paper"]
        adaptive = {
            "anchor_paper": self._adaptive_paper_dump(paper),
            "inferred_chapter": payload.get("inferred_chapter"),
            "inferred_kps": payload.get("inferred_kps"),
            "anchor_kps": payload.get("anchor_kps"),
            "semester": payload.get("semester"),
            "requested": payload.get("requested"),
            "delivered": payload.get("delivered"),
            "shortfall": payload.get("shortfall"),
        }
        session.metadata["adaptive"] = adaptive
        mark_assessment_started(session)
        self._record_decision(
            session,
            self._assessment.name,
            SessionPhase.ASSESS,
            "adaptive anchor assessment generated",
            ok=True,
        )
        self._store.save(session)
        return payload

    @with_session_lock
    def continue_adaptive_assessment(
        self,
        session_id: str,
        anchor_results: list[dict],
    ) -> dict:
        """Build full 20-item paper from anchor results and set session.paper."""
        session = self._store.load(session_id)
        adaptive_meta = dict(session.metadata.get("adaptive") or {})
        semester = adaptive_meta.get("semester")
        payload = self._assessment.generate_adaptive_assessment(
            session.profile,
            is_first_time=False,
            anchor_results=anchor_results,
            semester=semester if isinstance(semester, str) else None,
            portrait=session.portrait,
        )
        paper: AssessmentPaper = payload["paper"]
        paper, validator_summary = self._validate_and_revise_paper(session, paper)
        payload["paper"] = paper

        adaptive_meta.update(
            {
                "anchor_results": anchor_results,
                "full_paper": self._adaptive_paper_dump(paper),
                "diagnosis": payload.get("diagnosis"),
                "inferred_chapter": payload.get("inferred_chapter"),
                "inferred_kps": payload.get("inferred_kps"),
                "target_kps": payload.get("target_kps"),
                "requested": payload.get("requested"),
                "delivered": payload.get("delivered"),
                "shortfall": payload.get("shortfall"),
            }
        )
        session.metadata["adaptive"] = adaptive_meta
        session.paper = paper
        self._bind_pending_questions(session, paper)
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.diagnosis = None
        session.plan = None
        self._set_phase(session, SessionPhase.PRACTICE)
        self._record_decision(
            session,
            self._assessment.name,
            SessionPhase.ASSESS,
            "adaptive full assessment generated",
            ok=True,
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
        return payload

    @with_session_lock
    def submit(
        self,
        session_id: str,
        answers: dict[str, str],
        *,
        item_meta: dict[str, dict] | None = None,
    ) -> SessionState:
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("submit", session)
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
        if is_assessment_timed_out(session):
            apply_submit_timeout(session, paper.items)
        session.grades = []
        session.diagnosis = None
        session.plan = None
        self._set_phase(session, SessionPhase.GRADE)
        return self._store.save(session)

    @with_session_lock
    def grade(self, session_id: str) -> list[GradeResult]:
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("grade", session)
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
        self._update_hint_outcomes(session)
        session.diagnosis = None
        session.plan = None
        self._set_phase(session, result.phase)
        self._record_decision(
            session,
            self._practice.name,
            SessionPhase.GRADE,
            "answers graded",
            evidence_ids=[event.evidence_id for event in evidence_events],
        )
        self._store.save(session)
        return session.grades

    @staticmethod
    def _update_hint_outcomes(session: SessionState) -> None:
        """Backfill HintInteraction.solved_after_hint from latest grades."""
        if not session.hint_interactions or not session.grades:
            return
        by_item = {g.item_id: g for g in session.grades}
        for item_id, rows in list(session.hint_interactions.items()):
            grade = by_item.get(item_id)
            if grade is None or not rows:
                continue
            solved = bool(grade.final_correct)
            session.hint_interactions[item_id] = [
                row.model_copy(update={"solved_after_hint": solved}) for row in rows
            ]

    @staticmethod
    def _frustration_level(session: SessionState) -> float:
        portrait = session.portrait
        if portrait is None:
            return 0.0
        return float(portrait.dimensions.emotional.get("frustration", 0.0) or 0.0)

    @with_session_lock
    def diagnose(self, session_id: str) -> DiagnosisReport:
        session = self._store.load(session_id)
        self._require_paper(session)
        PhaseGuard.assert_ready_for("diagnose", session)
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
        if result.payload.get("diagnosis_enrichment") is not None:
            session.metadata["diagnosis_enrichment"] = result.payload[
                "diagnosis_enrichment"
            ]
        session.plan = None
        self._set_phase(session, result.phase)
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

    @with_session_lock
    def plan(self, session_id: str) -> LearningPlanReport:
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("plan", session)
        result, degraded = run_with_quality_gate(
            lambda: self._planning.run(
                self._ctx(
                    session,
                    phase=SessionPhase.PLAN,
                    metadata={
                        "citations": list(session.curriculum_citations),
                        "diagnosis_enrichment": session.metadata.get(
                            "diagnosis_enrichment"
                        )
                        or {},
                    },
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
        if result.payload.get("scientific_plan") is not None:
            session.metadata["scientific_plan"] = result.payload["scientific_plan"]
        for entry in result.payload.get("plan_history_append", []):
            session.plan_history.append(entry)
        self._set_phase(session, result.phase)
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

    @staticmethod
    def _phase_after_planning(
        session: SessionState,
        agent_phase: SessionPhase,
        *,
        replan: bool = False,
    ) -> SessionPhase:
        """Map planning agent phase to a legal session phase."""
        if agent_phase != SessionPhase.PRACTICE_LOOP:
            return agent_phase
        if replan:
            # Replan updates plan content only; do not restart consolidation.
            if session.phase in (
                SessionPhase.PRACTICE,
                SessionPhase.PRACTICE_LOOP,
                SessionPhase.PLAN,
            ):
                return session.phase
            return SessionPhase.PLAN
        return SessionPhase.PRACTICE_LOOP

    @with_session_lock
    def request_replan(self, session_id: str) -> LearningPlanReport:
        """Re-run planning with current portrait/diagnosis; supersede prior plan."""
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("replan", session)
        result = self._planning.run(
            self._ctx(
                session,
                phase=SessionPhase.PLAN,
                metadata={
                    "citations": list(session.curriculum_citations),
                    "diagnosis_enrichment": session.metadata.get(
                        "diagnosis_enrichment"
                    )
                    or {},
                },
            )
        )
        assert_writes_allowed(
            self._planning.name,
            set(result.payload) & {"plan", "plan_history_append"},
        )
        session.plan = result.payload["plan"]
        if result.payload.get("scientific_plan") is not None:
            session.metadata["scientific_plan"] = result.payload["scientific_plan"]
        for entry in result.payload.get("plan_history_append", []):
            session.plan_history.append(entry)
        target_phase = self._phase_after_planning(
            session, result.phase, replan=True
        )
        if target_phase != session.phase:
            self._set_phase(session, target_phase)
        self._record_decision(
            session,
            self._planning.name,
            SessionPhase.PLAN,
            "learning plan revised",
        )
        self._store.save(session)
        return session.plan

    @with_session_lock
    def tutor_start(self, session_id: str, item_id: str) -> TutorTurn:
        """Begin Socratic tutoring for an assessment/practice item (grades optional)."""
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("tutor", session)
        paper = self._require_paper_for_tutor(session)
        item = next((i for i in paper.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item id: {item_id}")
        grade = next((g for g in session.grades if g.item_id == item_id), None)
        error_tag = grade.error_tags[0] if grade and grade.error_tags else None
        turn = self._tutor.start(
            item, error_tag, frustration=self._frustration_level(session)
        )
        turn = self._guard_turn(session, item, turn)
        session.tutor_by_item[item_id] = turn
        self._record_decision(
            session,
            self._tutor.name,
            session.phase,
            "tutoring started",
        )
        self._store.save(session)
        return turn

    @with_session_lock
    def tutor_step(
        self, session_id: str, item_id: str, user_message: str
    ) -> TutorTurn:
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("tutor", session)
        paper = self._require_paper_for_tutor(session)
        item = next((row for row in paper.items if row.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item id: {item_id}")
        previous = session.tutor_by_item.get(item_id)
        if previous is None:
            raise ValueError("tutoring has not started for this item")
        used = session.hint_interactions.get(item_id, [])
        if len(used) >= MAX_HINTS_PER_ITEM:
            from ilearn.core.user_errors import UserFriendlyError

            raise UserFriendlyError(
                "E-014",
                technical_detail="hints exhausted for this item",
            )
        enrichment = session.metadata.get("diagnosis_enrichment")
        diagnosis_ctx = (
            enrichment if isinstance(enrichment, dict) else None
        )
        frustration = self._frustration_level(session)
        if previous.error_tag or diagnosis_ctx:
            turn = self._tutor.get_socratic_hint_with_diagnosis(
                item,
                user_message,
                diagnosis_ctx,
                phase=previous.phase,
                error_tag=previous.error_tag,
                frustration=frustration,
            )
        else:
            turn = self._tutor.step(
                previous.phase,
                user_message,
                item,
                previous.error_tag,
                frustration=frustration,
            )
        turn = self._guard_turn(session, item, turn)
        session.tutor_by_item[item_id] = turn
        session.hint_interactions.setdefault(item_id, []).append(
            HintInteraction(
                item_id=item_id,
                turn=len(used) + 1,
                user_input=user_message,
                ai_hint=turn.message,
            )
        )
        self._record_decision(
            session,
            self._tutor.name,
            session.phase,
            "tutoring hint",
        )
        self._store.save(session)
        return turn

    def _guard_turn(
        self, session: SessionState, item, turn: TutorTurn
    ) -> TutorTurn:
        verdict = self._guard.check(turn.message, item.answer_key)
        if verdict.is_leak and verdict.confidence > 0.7:
            self._record_decision(
                session,
                "guard",
                SessionPhase.PRACTICE,
                f"leak blocked ({verdict.reason})",
                ok=False,
            )
            return turn.model_copy(update={"message": SAFE_FALLBACK})
        return turn

    @with_session_lock
    def run_after_submit(self, session_id: str) -> SessionState:
        self.grade(session_id)
        self.diagnose(session_id)
        self.plan(session_id)
        session = self._store.load(session_id)
        if session.phase == SessionPhase.PRACTICE_LOOP:
            self.start_practice_loop(session_id)
        return self._store.load(session_id)

    @with_session_lock
    def start_practice_loop(self, session_id: str) -> AssessmentPaper:
        session = self._store.load(session_id)
        PhaseGuard.assert_ready_for("practice_loop", session)
        weak_ids = [
            mastery.knowledge_id
            for mastery in session.diagnosis.knowledge_mastery
            if mastery.level == "weak"
        ][:5]
        if not weak_ids:
            from ilearn.core.user_errors import UserFriendlyError

            raise UserFriendlyError(
                "E-015",
                technical_detail="practice loop requires weak knowledge ids",
            )

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
        self._set_phase(session, result.phase)
        self._store.save(session)
        return session.paper

    @with_session_lock
    def report(self, session_id: str) -> str:
        return render_full_report(self._store.load(session_id))

    @staticmethod
    def _require_paper(session: SessionState) -> AssessmentPaper:
        if session.paper is None:
            from ilearn.core.user_errors import UserFriendlyError

            raise UserFriendlyError(
                "E-011",
                technical_detail="session must have an assessment paper",
            )
        return session.paper

    @staticmethod
    def _require_paper_for_tutor(session: SessionState) -> AssessmentPaper:
        paper = paper_for_tutor(session)
        if paper is None:
            from ilearn.core.user_errors import UserFriendlyError

            raise UserFriendlyError(
                "E-011",
                technical_detail="session must have an assessment paper",
            )
        return paper
