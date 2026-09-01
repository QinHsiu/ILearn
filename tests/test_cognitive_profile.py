"""Tests for cognitive skill graph loading."""

from __future__ import annotations

from pathlib import Path

from ilearn.core.cognitive_profile import CognitiveDimension, CognitiveSkillGraph, dimension_label

FIXTURE = Path(__file__).parent / "fixtures" / "cognitive_skills_tiny.json"


def test_load_skill_and_prereqs():
    g = CognitiveSkillGraph(FIXTURE)
    node = g.get("fraction_001")
    assert node is not None
    assert node.dimension == CognitiveDimension.UNDERSTAND
    assert node.knowledge_point == "分数的意义"
    assert g.get_prerequisites("fraction_002") == ["fraction_001"]
    assert len(g.by_knowledge_point("分数的意义")) >= 1


def test_dimension_label_chinese():
    assert dimension_label(CognitiveDimension.UNDERSTAND) == "理解"
    assert dimension_label("apply") == "应用"
