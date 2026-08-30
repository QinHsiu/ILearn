"""Edge-case diagnosis / planning enrichment (Edition 0830_3)."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.planning import PlanningAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_diagnosis_marks_insufficient_data_without_grades():
    agent = DiagnosisAgent(PilotBeijingRenjiaoProvider(PILOT))
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="i1",
                stem="q",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_mult"],
                answer_key="A",
            )
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        grades=[],
        evidence_log=[],
    )
    result = agent.run(ctx)
    enrichment = result.payload["diagnosis_enrichment"]
    assert enrichment["data_status"] == "insufficient_data"
    assert "insufficient_data" in result.payload["diagnosis"].flags


def test_planning_pending_when_limited_data():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="beijing-renjiao",
        knowledge_mastery=[],
        interventions=[],
    )
    out = agent.generate_scientific_plan(
        diagnosis,
        StudentProfile(region="北京", grade=5, age=11),
        enrichment={"data_status": "limited_data", "weak_skills": []},
    )
    assert out["status"] == "pending"
    assert out["tasks"] == []


def test_planning_completed_when_no_weak_skills():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="beijing-renjiao",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="frac_mult", score_rate=0.9, level="mastered")
        ],
        interventions=[],
    )
    out = agent.generate_scientific_plan(
        diagnosis,
        StudentProfile(region="北京", grade=5, age=11),
        enrichment={"data_status": "ok", "weak_skills": []},
    )
    assert out["status"] == "completed"
