"""Tests for cognitive-profile diagnosis enrichment (Edition 0830)."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.core.cognitive_profile import CognitiveSkillGraph
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
FIXTURE = Path(__file__).parent / "fixtures" / "cognitive_skills_tiny.json"


def test_cognitive_diagnosis_prereq_gap():
    agent = DiagnosisAgent(
        PilotBeijingRenjiaoProvider(PILOT),
        cognitive_graph=CognitiveSkillGraph(FIXTURE),
    )
    evidence = [{"skill_id": "fraction_002", "is_correct": False}]
    out = agent.diagnose_with_cognitive_profile(evidence, skill_id="fraction_002")
    assert out["root_cause"] == "前置技能缺失"
    assert out["gap_skill"] == "fraction_001"


def test_cognitive_diagnosis_dimension_gap_when_prereq_ok():
    agent = DiagnosisAgent(
        PilotBeijingRenjiaoProvider(PILOT),
        cognitive_graph=CognitiveSkillGraph(FIXTURE),
    )
    evidence = [
        {"skill_id": "fraction_001", "is_correct": True},
        {"skill_id": "fraction_001", "is_correct": True},
        {"skill_id": "fraction_002", "is_correct": False},
    ]
    out = agent.diagnose_with_cognitive_profile(evidence, skill_id="fraction_002")
    assert "层次不足" in out["root_cause"]
    assert out["gap_skill"] == "fraction_002"
    assert out["dimension"] == "apply"
