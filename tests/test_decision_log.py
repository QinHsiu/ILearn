from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.protocol import AgentResult
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    LearnerPortrait,
    LearningPlanReport,
    SessionPhase,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> tuple[MultiAgentOrchestrator, SessionStore]:
    store = SessionStore(tmp_path)
    return (
        MultiAgentOrchestrator(
            store=store,
            curriculum=PilotBeijingRenjiaoProvider(PILOT),
            llm=None,
        ),
        store,
    )


def _completed_session(
    orchestrator: MultiAgentOrchestrator,
) -> tuple[str, AssessmentPaper]:
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    paper = orchestrator.generate_assessment(session_id)
    orchestrator.submit(
        session_id,
        {item.id: item.answer_key or "" for item in paper.items},
    )
    orchestrator.run_after_submit(session_id)
    return session_id, paper


def test_pipeline_appends_persisted_agent_decisions(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)

    session_id, _ = _completed_session(orchestrator)

    decisions = store.load(session_id).decision_log
    assert [decision.agent for decision in decisions] == [
        "assessment",
        "practice",
        "diagnosis",
        "planning",
    ]
    assert [decision.phase for decision in decisions] == [
        SessionPhase.ASSESS,
        SessionPhase.GRADE,
        SessionPhase.DIAGNOSE,
        SessionPhase.PLAN,
    ]
    assert len(decisions) >= 3
    assert decisions[-1].agent == "planning"
    assert all(decision.reason for decision in decisions)


def test_replan_and_tutor_start_append_persisted_decisions(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id, paper = _completed_session(orchestrator)

    orchestrator.request_replan(session_id)
    orchestrator.tutor_start(session_id, paper.items[0].id)

    decisions = store.load(session_id).decision_log
    assert [decision.agent for decision in decisions[-2:]] == ["planning", "tutor"]
    assert [decision.phase for decision in decisions[-2:]] == [
        SessionPhase.PLAN,
        SessionPhase.PRACTICE,
    ]


class _InvalidAssessmentAgent:
    name = "assessment"

    def run(self, ctx):
        return AgentResult(
            phase=SessionPhase.PRACTICE,
            payload={
                "paper": AssessmentPaper(
                    items=[],
                    grade=ctx.profile.grade,
                    curriculum_label="test",
                )
            },
        )


class _InvalidDiagnosisAgent:
    name = "diagnosis"

    def run(self, ctx):
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={
                "diagnosis": DiagnosisReport(curriculum_label="test"),
                "portrait": ctx.portrait
                or LearnerPortrait(student_key="test_g5"),
            },
        )


class _InvalidPlanningAgent:
    name = "planning"

    def run(self, _ctx):
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={"plan": LearningPlanReport(goal="", markdown="")},
        )


def test_quality_gate_degradation_is_recorded_for_gated_agents(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )

    orchestrator._assessment = _InvalidAssessmentAgent()
    paper = orchestrator.generate_assessment(session_id)
    assessment_decision = store.load(session_id).decision_log[-1]

    orchestrator.submit(session_id, {paper.items[0].id: ""})
    orchestrator.grade(session_id)
    orchestrator._diagnosis = _InvalidDiagnosisAgent()
    orchestrator.diagnose(session_id)
    diagnosis_decision = store.load(session_id).decision_log[-1]

    orchestrator._planning = _InvalidPlanningAgent()
    orchestrator.plan(session_id)
    planning_decision = store.load(session_id).decision_log[-1]

    assert assessment_decision.degraded is True
    assert diagnosis_decision.degraded is True
    assert planning_decision.degraded is True
    assert assessment_decision.ok is False
    assert diagnosis_decision.ok is False
    assert planning_decision.ok is False


def test_grade_decision_references_emitted_evidence(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    paper = orchestrator.generate_assessment(session_id)
    orchestrator.submit(
        session_id,
        {item.id: item.answer_key or "" for item in paper.items},
    )

    orchestrator.grade(session_id)

    session = store.load(session_id)
    grade_decision = session.decision_log[-1]
    assert grade_decision.agent == "practice"
    assert grade_decision.evidence_ids == [
        event.evidence_id for event in session.evidence_log
    ]
