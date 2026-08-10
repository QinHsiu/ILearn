from pathlib import Path

from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.schemas import GradeResult, StudentAnswer, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_practice_agent_attaches_hint_on_incorrect_grade():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    item = paper.items[0]
    agent = PracticeAgent(llm=None)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=[StudentAnswer(item_id=item.id, answer_text="wrong answer")],
    )
    result = agent.run(ctx)
    hints = result.payload.get("hints", {})
    grades = result.payload["grades"]
    incorrect = [g for g in grades if not g.final_correct]
    assert incorrect
    grade = incorrect[0]
    assert grade.hint_level_suggestion in ("low", "medium", "high")
    assert grade.item_id in hints
    assert item.answer_key not in hints[grade.item_id]
    if item.answer_key:
        assert item.answer_key not in hints[grade.item_id]
