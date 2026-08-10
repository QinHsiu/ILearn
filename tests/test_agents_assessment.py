from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_assessment_agent_builds_20_item_paper():
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT))
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    result = agent.run(ctx)
    paper = result.payload["paper"]
    assert len(paper.items) == 20
    assert result.phase == SessionPhase.PRACTICE


def test_assessment_agent_followup_filters_weak_nodes():
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT))
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PRACTICE_LOOP,
        profile=StudentProfile(region="北京", grade=5, age=11),
        metadata={"weak_knowledge_ids": ["frac_add_same"], "paper_type": "followup"},
    )
    result = agent.run(ctx)
    paper = result.payload["paper"]
    assert 1 <= len(paper.items) <= 10
    assert all(
        any(k in ctx.metadata["weak_knowledge_ids"] for k in item.knowledge_ids)
        for item in paper.items
    )
