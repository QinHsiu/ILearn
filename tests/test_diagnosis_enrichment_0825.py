"""Tests for diagnosis prerequisite enrichment."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_diagnosis_enrichment_includes_prerequisite_gaps():
    agent = DiagnosisAgent(PilotBeijingRenjiaoProvider(PILOT))
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="i1",
                stem="q1",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_mult"],
                answer_key="A",
            ),
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        grades=[
            GradeResult(
                item_id="i1",
                final_correct=False,
                error_tags=["concept_gap"],
                knowledge_ids=["frac_mult"],
            )
        ],
    )
    result = agent.run(ctx)
    enrichment = result.payload["diagnosis_enrichment"]
    assert "frac_mult" in enrichment["weak_skills"] or enrichment["weak_skills"]
    assert "frac_add_same" in enrichment["prerequisite_gaps"]
    assert enrichment["learning_advice"]
    assert "prerequisite_gaps" in result.payload["diagnosis"].flags
