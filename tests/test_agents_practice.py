from pathlib import Path

from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.schemas import StudentAnswer, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_practice_agent_grades_text_answers_offline():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    answers = [StudentAnswer(item_id=item.id, answer_text=item.answer_key or "") for item in paper.items[:3]]
    agent = PracticeAgent(llm=None)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=answers,
    )
    result = agent.run(ctx)
    grades = result.payload["grades"]
    assert len(grades) == 3
    assert all(g.final_correct for g in grades)
    assert result.phase == SessionPhase.DIAGNOSE


def test_practice_agent_first_pass_grades_use_probe_lane():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    answers = [StudentAnswer(item_id=item.id, answer_text=item.answer_key or "") for item in paper.items[:3]]
    agent = PracticeAgent(llm=None)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=answers,
        loop_count=0,
    )
    result = agent.run(ctx)
    grades = result.payload["grades"]
    assert grades
    assert all(g.lane == "probe" for g in grades)
    evidence = result.payload["evidence"]
    assert evidence
    assert all(e.lane == "probe" for e in evidence)


def test_practice_agent_followup_loop_grades_use_practice_lane():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    answers = [StudentAnswer(item_id=item.id, answer_text=item.answer_key or "") for item in paper.items[:3]]
    agent = PracticeAgent(llm=None)
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=answers,
        loop_count=1,
    )
    result = agent.run(ctx)
    grades = result.payload["grades"]
    assert grades
    assert all(g.lane == "practice" for g in grades)
