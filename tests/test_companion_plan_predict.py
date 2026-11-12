"""Companion Plan / Predict Phase-1 ultimate gates."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.companion import CompanionAgent
from ilearn.core.companion_predict import build_risk_forecast
from ilearn.core.companion_week_plan import build_week_plan
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionPhase,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider


def _agent() -> CompanionAgent:
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    return CompanionAgent(PilotBeijingRenjiaoProvider(pilot), llm=None)


def test_week_plan_has_seven_days():
    session = SessionState(
        session_id="p",
        profile=StudentProfile(region="北京", grade=5, age=11),
        phase=SessionPhase.IDLE,
    )
    plan = build_week_plan(session)
    assert len(plan["days"]) == 7
    assert plan["source"] == "stage_default"


def test_week_plan_uses_diagnosis_weaks():
    session = SessionState(
        session_id="p",
        profile=StudentProfile(region="北京", grade=5, age=11),
        phase=SessionPhase.PLAN,
        diagnosis=DiagnosisReport(
            curriculum_label="北京·人教",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="k1",
                    knowledge_name="分数加减",
                    level="weak",
                    score_rate=0.2,
                )
            ],
        ),
    )
    plan = build_week_plan(session)
    assert plan["source"] == "diagnosis"
    assert "分数加减" in plan["weak_focus"]


def test_predict_high_without_evidence():
    session = SessionState(
        session_id="p",
        profile=StudentProfile(region="北京", grade=8, age=14),
        phase=SessionPhase.IDLE,
    )
    forecast = build_risk_forecast(session)
    assert forecast["level"] in {"medium", "high"}
    assert forecast["evidence_count"] == 0


def test_senior_high_answer_cites_b2_pack():
    agent = _agent()
    session = SessionState(
        session_id="sh",
        profile=StudentProfile(region="北京", grade=10, age=16),
        phase=SessionPhase.IDLE,
    )
    reply = agent.chat(session, "什么是函数？请讲一下")
    assert reply.intent == "answer"
    assert reply.citations


def test_undergrad_life_stage_pack():
    agent = _agent()
    session = SessionState(
        session_id="ug",
        profile=StudentProfile(
            region="北京", grade=12, age=18, life_stage="undergrad"
        ),
        phase=SessionPhase.IDLE,
    )
    reply = agent.chat(session, "什么是微积分？请讲一下")
    assert reply.intent == "answer"
    assert reply.citations
    assert any("微积分" in (c.title + c.excerpt) for c in reply.citations)
