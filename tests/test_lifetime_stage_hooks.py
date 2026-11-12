"""Lifelong stage hooks: career / midlife / elder packs + age inference."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.companion import CompanionAgent, infer_life_stage
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider


def _agent() -> CompanionAgent:
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    return CompanionAgent(PilotBeijingRenjiaoProvider(pilot), llm=None)


def test_infer_life_stage_by_age():
    assert (
        infer_life_stage(StudentProfile(region="北京", grade=12, age=30)) == "career"
    )
    assert (
        infer_life_stage(StudentProfile(region="北京", grade=12, age=50)) == "midlife"
    )
    assert infer_life_stage(StudentProfile(region="北京", grade=12, age=70)) == "elder"


def test_career_answer_cites_pack():
    agent = _agent()
    session = SessionState(
        session_id="c",
        profile=StudentProfile(
            region="北京", grade=12, age=28, life_stage="career"
        ),
        phase=SessionPhase.IDLE,
    )
    reply = agent.chat(session, "怎么做职场技能练习？请讲一下")
    assert reply.intent == "answer"
    assert reply.citations


def test_elder_plan_uses_stage_focus():
    agent = _agent()
    session = SessionState(
        session_id="e",
        profile=StudentProfile(region="北京", grade=12, age=72, life_stage="elder"),
        phase=SessionPhase.IDLE,
    )
    reply = agent.chat(session, "帮我规划本周学习")
    assert reply.intent == "plan"
    assert "周一" in reply.reply
    assert session.metadata["companion_week_plan"]["life_stage"] == "elder"
