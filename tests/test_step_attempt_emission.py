from pathlib import Path

from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.schemas import AssessmentPaper, StudentAnswer, StudentProfile, StepAttempt
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_practice_agent_emits_step_attempts_aligned_to_rubric():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum).build(StudentProfile(region="北京", grade=5, age=11))
    constructed = next(i for i in paper.items if i.type == "constructed" and i.rubric_steps)
    tight = AssessmentPaper(
        items=[constructed],
        grade=5,
        curriculum_label=paper.curriculum_label,
    )
    answers = [StudentAnswer(item_id=constructed.id, answer_text=constructed.answer_key or "")]
    result = PracticeAgent(llm=None).run(
        AgentContext(
            session_id="s1",
            phase=SessionPhase.GRADE,
            profile=StudentProfile(region="北京", grade=5, age=11),
            paper=tight,
            answers=answers,
        )
    )
    attempts = result.payload["step_attempts"]
    assert attempts
    assert all(isinstance(a, StepAttempt) for a in attempts)
    assert {a.step_index for a in attempts} <= set(range(len(constructed.rubric_steps)))
