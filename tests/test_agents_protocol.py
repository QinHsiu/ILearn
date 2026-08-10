from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import ImageAnswer, LearnerPortrait, StudentProfile


def test_session_phase_values():
    assert SessionPhase.ASSESS.value == "assess"
    assert SessionPhase.PRACTICE_LOOP.value == "practice_loop"


def test_image_answer_accepts_base64():
    ImageAnswer(item_id="q1", image_base64="aGVsbG8=", mime_type="image/png")


def test_learner_portrait_defaults():
    p = LearnerPortrait(student_key="beijing_g5")
    assert p.weakness_log == []
    assert p.knowledge_state == {}


def test_agent_context_carries_phase():
    ctx = AgentContext(
        session_id="abc",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    assert ctx.phase == SessionPhase.GRADE
