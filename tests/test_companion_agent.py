"""Companion Ask/Answer router with speech I/O envelopes."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.companion import CompanionAgent, infer_life_stage
from ilearn.core.schemas import (
    CompanionMode,
    CompanionPerceptionIn,
    SessionPhase,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider


def _session(**kwargs) -> SessionState:
    profile = StudentProfile(region="北京", grade=5, age=11, **kwargs)
    return SessionState(session_id="c1", profile=profile, phase=SessionPhase.IDLE)


def test_infer_life_stage_from_grade():
    assert infer_life_stage(StudentProfile(region="北京", grade=5, age=11)) == "primary"
    assert infer_life_stage(StudentProfile(region="北京", grade=8, age=14)) == "junior_high"
    assert infer_life_stage(StudentProfile(region="北京", grade=11, age=17)) == "senior_high"


def test_route_ask_when_goal_unclear():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    reply = agent.chat(_session(), "我想学")
    assert reply.intent == "ask"
    assert reply.reply
    assert reply.speech.speakable is True
    assert reply.speech.ssml_or_text == reply.reply
    assert reply.input_modality == "text"


def test_route_answer_for_concept_question():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    reply = agent.chat(_session(), "什么是小数乘法？请讲一下")
    assert reply.intent == "answer"
    assert reply.reply
    assert reply.speech.ssml_or_text
    # citation or explicit miss
    assert reply.citations or ("未命中" in reply.reply or "没有找到" in reply.reply)


def test_route_evaluate_when_user_asks_for_test():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    reply = agent.chat(_session(), "给我出一套测评卷")
    assert reply.intent == "evaluate"
    assert any(a.type == "start_assessment" for a in reply.actions)


def test_plan_predict_are_stubs():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    plan = agent.chat(_session(), "帮我规划一下本周学习")
    assert plan.intent == "plan"
    assert "下一期" in plan.reply or "尚未" in plan.reply
    pred = agent.chat(_session(), "预测我下周能学会吗")
    assert pred.intent == "predict"


def test_speech_perception_input_sets_modality():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    reply = agent.chat(
        _session(),
        message=None,
        perception=CompanionPerceptionIn(
            source_type="speech",
            text="什么是小数乘法",
            audio_ref="utt://demo.wav",
            confidence=0.9,
        ),
        mode="open_learn",
    )
    assert reply.input_modality == "speech"
    assert reply.speech.speakable is True
    assert reply.intent in {"ask", "answer"}


def test_exam_mode_redacts_answer_key_phrases():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot))
    reply = agent.chat(
        _session(),
        "正确答案是多少？直接告诉我答案",
        mode="exam_tutor",
    )
    assert "答案是" not in reply.reply or reply.intent == "ask"
    assert reply.mode == "exam_tutor"
