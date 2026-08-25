"""Tests for adaptive cold-start assessment generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
BEIJING = "\u5317\u4eac"
SPRING = "\u4e0b\u5b66\u671f"


def _agent() -> AssessmentAgent:
    return AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT))


def test_adaptive_anchor_paper_uses_inferred_knowledge():
    agent = _agent()
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    result = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=SPRING,
        now=datetime(2026, 4, 1),
    )
    assert result["is_anchor"] is True
    assert result["inferred_kps"]
    assert result["anchor_kps"]
    assert 1 <= result["delivered"] <= 8
    assert result["requested"] <= 8
    assert result["shortfall"] == max(0, result["requested"] - result["delivered"])
    paper = result["paper"]
    assert len(paper.items) == result["delivered"]
    # Anchor must not invent a 20-item fixed paper.
    assert len(paper.items) != 20 or result["requested"] == 20


def test_adaptive_continue_builds_exactly_20_item_paper():
    agent = _agent()
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    anchor = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=SPRING,
        now=datetime(2026, 4, 1),
    )
    results = []
    for item in anchor["paper"].items:
        results.append(
            {
                "item_id": item.id,
                "knowledge_ids": list(item.knowledge_ids),
                "is_correct": False,
            }
        )
    full = agent.generate_adaptive_assessment(
        profile,
        is_first_time=False,
        anchor_results=results,
        semester=SPRING,
        now=datetime(2026, 4, 1),
    )
    assert full["is_anchor"] is False
    assert len(full["paper"].items) == 20
    assert full["requested"] == 20
    assert full["delivered"] == 20
    assert full["shortfall"] == 0
    assert "frac_add_same" in full["diagnosis"]["weak_knowledge_points"] or full[
        "diagnosis"
    ]["weak_knowledge_points"]


def test_default_run_still_builds_20_items():
    from ilearn.agents.protocol import AgentContext, SessionPhase

    agent = _agent()
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=StudentProfile(region=BEIJING, grade=5, age=11),
    )
    paper = agent.run(ctx).payload["paper"]
    assert len(paper.items) == 20
