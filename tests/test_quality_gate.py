from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.protocol import AgentResult
from ilearn.core.quality_gate import run_with_quality_gate
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    KnowledgeMastery,
    LearnerPortrait,
    LearningPlanReport,
    SessionPhase,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_quality_gate_retries_once_then_returns_valid_result():
    attempts = iter([{"valid": False}, {"valid": True}])
    call_count = 0

    def run_once():
        nonlocal call_count
        call_count += 1
        return next(attempts)

    result, degraded = run_with_quality_gate(
        run_once,
        lambda value: value["valid"],
    )

    assert result == {"valid": True}
    assert degraded is False
    assert call_count == 2


def test_quality_gate_degrades_after_retry_is_exhausted():
    call_count = 0

    def run_once():
        nonlocal call_count
        call_count += 1
        return {"valid": False, "attempt": call_count}

    result, degraded = run_with_quality_gate(
        run_once,
        lambda value: value["valid"],
    )

    assert result == {"valid": False, "attempt": 2}
    assert degraded is True
    assert call_count == 2


class _InvalidAssessmentAgent:
    name = "assessment"

    def __init__(self) -> None:
        self.call_count = 0

    def run(self, ctx):
        self.call_count += 1
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

    def __init__(self) -> None:
        self.call_count = 0

    def run(self, ctx):
        self.call_count += 1
        assert ctx.portrait is not None
        ctx.portrait.knowledge_state["rejected-mutation"] = 1.0
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={
                "diagnosis": DiagnosisReport(curriculum_label="test"),
                "portrait": ctx.portrait,
            },
        )


class _InvalidThenValidMutatingDiagnosisAgent:
    name = "diagnosis"

    def __init__(self) -> None:
        self.call_count = 0

    def run(self, ctx):
        self.call_count += 1
        assert ctx.portrait is not None
        mutation_count = ctx.portrait.knowledge_state.get("retry-mutation", 0.0) + 1
        ctx.portrait.knowledge_state["retry-mutation"] = mutation_count
        mastery = (
            []
            if self.call_count == 1
            else [
                KnowledgeMastery(
                    knowledge_id="valid-kc",
                    score_rate=1.0,
                    level="mastered",
                )
            ]
        )
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={
                "diagnosis": DiagnosisReport(
                    knowledge_mastery=mastery,
                    curriculum_label="test",
                ),
                "portrait": ctx.portrait,
            },
        )


class _InvalidPlanningAgent:
    name = "planning"

    def __init__(self) -> None:
        self.call_count = 0

    def run(self, _ctx):
        self.call_count += 1
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={"plan": LearningPlanReport(goal="", markdown="")},
        )


def _orchestrator(tmp_path):
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    return orchestrator, store, session_id


def test_assessment_quality_failure_retries_then_returns_minimal_paper(tmp_path):
    orchestrator, store, session_id = _orchestrator(tmp_path)
    invalid_agent = _InvalidAssessmentAgent()
    orchestrator._assessment = invalid_agent

    paper = orchestrator.generate_assessment(session_id)

    assert invalid_agent.call_count == 2
    assert len(paper.items) == 1
    assert paper.paper_version == "degraded"
    assert store.load(session_id).paper == paper


def test_diagnosis_quality_failure_retries_then_returns_minimal_report(tmp_path):
    orchestrator, store, session_id = _orchestrator(tmp_path)
    paper = orchestrator.generate_assessment(session_id)
    session = store.load(session_id)
    session.grades = [
        GradeResult(item_id=paper.items[0].id, final_correct=False)
    ]
    session.portrait = LearnerPortrait(student_key="test_g5")
    store.save(session)
    invalid_agent = _InvalidDiagnosisAgent()
    orchestrator._diagnosis = invalid_agent

    diagnosis = orchestrator.diagnose(session_id)

    assert invalid_agent.call_count == 2
    assert diagnosis.knowledge_mastery == []
    assert diagnosis.interventions == []
    assert "quality_gate_degraded" in diagnosis.flags
    persisted = store.load(session_id)
    assert persisted.diagnosis == diagnosis
    assert persisted.portrait is not None
    assert "rejected-mutation" not in persisted.portrait.knowledge_state


def test_diagnosis_retry_discards_mutations_from_rejected_attempt(tmp_path):
    orchestrator, store, session_id = _orchestrator(tmp_path)
    paper = orchestrator.generate_assessment(session_id)
    session = store.load(session_id)
    session.grades = [
        GradeResult(item_id=paper.items[0].id, final_correct=False)
    ]
    session.portrait = LearnerPortrait(student_key="test_g5")
    store.save(session)
    mutating_agent = _InvalidThenValidMutatingDiagnosisAgent()
    orchestrator._diagnosis = mutating_agent

    diagnosis = orchestrator.diagnose(session_id)

    persisted = store.load(session_id)
    assert mutating_agent.call_count == 2
    assert diagnosis.knowledge_mastery[0].knowledge_id == "valid-kc"
    assert persisted.portrait is not None
    assert persisted.portrait.knowledge_state["retry-mutation"] == 1.0


def test_plan_quality_failure_retries_then_returns_minimal_report(tmp_path):
    orchestrator, store, session_id = _orchestrator(tmp_path)
    session = store.load(session_id)
    session.diagnosis = DiagnosisReport(curriculum_label="test")
    store.save(session)
    invalid_agent = _InvalidPlanningAgent()
    orchestrator._planning = invalid_agent

    plan = orchestrator.plan(session_id)

    assert invalid_agent.call_count == 2
    assert plan.days == []
    assert plan.markdown
    assert plan.status == "draft"
    assert store.load(session_id).plan == plan
