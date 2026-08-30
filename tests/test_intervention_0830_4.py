"""Tests for intervention library and tutor skill hints."""

from __future__ import annotations

from ilearn.agents.tutor import TutorAgent
from ilearn.core.intervention_library import lookup_intervention
from ilearn.core.schemas import AssessmentItem


def test_lookup_intervention():
    hit = lookup_intervention("frac_add_same")
    assert hit is not None
    assert "分母" in hit["hint"]


def test_tutor_includes_skill_intervention():
    agent = TutorAgent()
    item = AssessmentItem(
        id="i1",
        stem="q",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
        answer_key="1",
    )
    turn = agent.step("locate_gap", "不会", item, "concept_gap")
    assert "同分母" in turn.message or "分母" in turn.message
