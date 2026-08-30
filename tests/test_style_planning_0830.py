"""Tests for learning-style planning adaptation (Edition 0830)."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.planning import PlanningAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    DiagnosisReport,
    Intervention,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _diagnosis() -> DiagnosisReport:
    return DiagnosisReport(
        curriculum_label="beijing-renjiao",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_mult", score_rate=0.2, level="weak"
            ),
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_mult",
                title="frac_mult",
                why="low score",
                what_to_fix_first="concept",
                priority=1,
            ),
        ],
    )


def test_personalized_plan_adds_style_adaptation():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    out = agent.generate_personalized_plan(_diagnosis(), "visual")
    assert out["learning_style"] == "visual"
    assert "diagram" in out["style_adaptation"]["material_type"]


def test_run_infers_style_from_behavior_metadata():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=_diagnosis(),
        metadata={
            "diagnosis_enrichment": {
                "weak_skills": ["frac_mult"],
                "prerequisite_gaps": [],
            },
            "behavior": {
                "diagram_expand_count": 8,
                "total_questions": 10,
                "audio_play_count": 0,
                "avg_response_time": 20,
                "visual_question_correct": 5,
                "visual_question_total": 5,
            },
        },
    )
    result = agent.run(ctx)
    scientific = result.payload["scientific_plan"]
    assert scientific["learning_style"] == "visual"
    assert "学习风格适配" in result.payload["plan"].markdown
