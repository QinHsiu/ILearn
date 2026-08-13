from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import KnowledgeEvidence, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


class _RecordingAgent:
    def __init__(self, agent) -> None:
        self._agent = agent
        self.name = agent.name
        self.contexts = []

    def run(self, ctx):
        self.contexts.append(ctx)
        return self._agent.run(ctx)


def test_phase2d_orchestration_contracts_work_together(tmp_path):
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    assessment = _RecordingAgent(orchestrator._assessment)
    diagnosis = _RecordingAgent(orchestrator._diagnosis)
    planning = _RecordingAgent(orchestrator._planning)
    orchestrator._assessment = assessment
    orchestrator._diagnosis = diagnosis
    orchestrator._planning = planning

    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    session = store.load(session_id)
    session.evidence_log = [
        KnowledgeEvidence(
            evidence_id=f"historical-{index}",
            session_id=session_id,
            item_id=f"old-item-{index}",
            knowledge_id="frac_add_same",
            lane="practice",
            correct=index % 2 == 0,
        )
        for index in range(45)
    ]
    store.save(session)

    paper = orchestrator.generate_assessment(session_id)
    pending = store.load(session_id).pending_questions
    assert [question.question_id for question in pending] == [
        item.id for item in paper.items
    ]
    assert [question.expected_answer for question in pending] == [
        item.answer_key or "" for item in paper.items
    ]

    orchestrator.submit(
        session_id,
        {item.id: item.answer_key or "" for item in paper.items},
    )
    completed = orchestrator.run_after_submit(session_id)

    assert len(assessment.contexts) == 1
    assert len(diagnosis.contexts) == 1
    assert len(planning.contexts) == 1
    for ctx in (assessment.contexts[0], diagnosis.contexts[0], planning.contexts[0]):
        assert ctx.profile == completed.profile
        assert len(ctx.evidence_log) <= 40
        assert "context_summary" in ctx.metadata

    assert completed.paper is not None
    assert completed.grades
    assert completed.diagnosis is not None
    assert completed.plan is not None
    assert [decision.agent for decision in completed.decision_log] == [
        "assessment",
        "item_validators",
        "practice",
        "diagnosis",
        "planning",
    ]
    assert all(decision.ok for decision in completed.decision_log)
    assert not any(decision.degraded for decision in completed.decision_log)
