from pathlib import Path

from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_curriculum_agent_returns_beijing_citations():
    agent = CurriculumAgent(pilot_dir=PILOT)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ONBOARD,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    result = agent.run(ctx)
    citations = result.payload["citations"]
    assert len(citations) >= 3
    assert all(c.source_label for c in citations)
    assert result.phase == SessionPhase.ONBOARD
