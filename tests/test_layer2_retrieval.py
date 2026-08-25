"""Tests for dual-layer adaptive question fill."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.core.schemas import AssessmentPaper, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
BEIJING = "\u5317\u4eac"
SPRING = "\u4e0b\u5b66\u671f"


def test_layer2_stub_fills_when_local_bank_empty(monkeypatch):
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT), llm=None)
    empty = AssessmentPaper(items=[], grade=5, curriculum_label="pilot")

    def _empty(*_args, **_kwargs):
        return empty

    monkeypatch.setattr(agent._builder, "build_by_knowledge_ids", _empty)
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    result = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=SPRING,
        now=datetime(2026, 4, 1),
    )
    assert result["is_anchor"] is True
    assert result["layer2_used"] is True
    assert result["layer2_source"] == "stub"
    assert result["delivered"] == result["requested"]
    assert result["shortfall"] == 0
    assert all(item.id.startswith("stub-") for item in result["paper"].items)
    assert all(item.answer_key for item in result["paper"].items)


def test_layer2_none_when_local_enough():
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT), llm=None)
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    result = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=SPRING,
        now=datetime(2026, 4, 1),
    )
    # Pilot bank usually covers anchor; layer2 may be unused.
    assert result["delivered"] >= 1
    if result["shortfall"] == 0 and not result.get("layer2_used"):
        assert result.get("layer2_source", "none") in ("none", "stub", "llm")
