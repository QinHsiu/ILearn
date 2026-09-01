"""Tests for scientific planning enrichment."""

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


def test_planning_appends_scientific_section_and_payload():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
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
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=StudentProfile(region="\u5317\u4eac", grade=5, age=11),
        diagnosis=diagnosis,
        metadata={
            "diagnosis_enrichment": {
                "weak_skills": ["frac_mult"],
                "prerequisite_gaps": ["frac_add_same"],
                "learning_advice": "test",
            }
        },
    )
    result = agent.run(ctx)
    plan = result.payload["plan"]
    scientific = result.payload["scientific_plan"]
    assert "\u79d1\u5b66\u5b66\u4e60\u65b9\u6cd5" in plan.markdown
    assert "分数乘法" in plan.markdown
    assert "frac_mult" not in plan.markdown
    assert "同分母分数加法" in plan.markdown
    assert any(t["type"] == "feynman" for t in scientific["tasks"])
    assert any(t["type"] == "review" for t in scientific["tasks"])
    assert scientific["review_schedule"]
    assert scientific["estimated_total_hours"] > 0
    assert isinstance(plan.days, list)
