"""Diagnosis enrichment keeps full evidence but presents a compacted view."""

from __future__ import annotations

from ilearn.agents.diagnosis import DiagnosisAgent
from ilearn.agents.protocol import AgentContext
from ilearn.core.context_compactor import ContextCompactor
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    KnowledgeEvidence,
    SessionPhase,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from pathlib import Path


def test_present_evidence_compacts_bulky_tool_rows():
    compactor = ContextCompactor(occupancy_trigger=0.5)
    messages = [
        {"role": "user", "content": "诊断"},
        {
            "role": "tool",
            "content": "x" * 500,
            "evidence_id": "ev1",
        },
        {
            "role": "tool",
            "content": "y" * 500,
            "evidence_id": "ev2",
        },
    ]
    out = compactor.auto_compact(messages, occupancy=0.9)
    assert out.layer == "auto"
    assert "ev1" in out.placeholders.values() or "ev1" in str(out.messages)
    assert all(
        not (m.get("role") == "tool" and len(str(m.get("content", ""))) > 400)
        for m in out.messages
    )


def test_diagnosis_enrichment_includes_compacted_presentation():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = DiagnosisAgent(PilotBeijingRenjiaoProvider(pilot))
    profile = StudentProfile(region="北京", grade=5, age=11)
    items = [
        AssessmentItem(
            id=f"q{i}",
            stem="1+1?",
            type="fill",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="2",
        )
        for i in range(5)
    ]
    paper = AssessmentPaper(
        curriculum_label="北京·人教·五年级",
        grade=5,
        items=items,
    )
    grades = [
        GradeResult(
            item_id=f"q{i}",
            final_correct=(i % 2 == 0),
            knowledge_ids=["dec_mult"],
            error_tags=[] if i % 2 == 0 else ["calc_error"],
        )
        for i in range(5)
    ]
    evidence = [
        KnowledgeEvidence(
            evidence_id=f"e{i}",
            session_id="s1",
            item_id=f"q{i}",
            knowledge_id="dec_mult",
            lane="probe",
            correct=(i % 2 == 0),
            error_tag=None if i % 2 == 0 else "calc_error",
        )
        for i in range(5)
    ]
    # Attach bulky tool-like presentation rows via metadata for compaction signal.
    bulky = [{"role": "tool", "content": "z" * 600, "evidence_id": f"e{i}"} for i in range(5)]
    result = agent.run(
        AgentContext(
            session_id="s1",
            phase=SessionPhase.DIAGNOSE,
            profile=profile,
            paper=paper,
            grades=grades,
            evidence_log=evidence,
            metadata={"context_messages": bulky, "context_occupancy": 0.95},
        )
    )
    enrichment = result.payload["diagnosis_enrichment"]
    assert "context_compaction" in enrichment
    assert enrichment["context_compaction"]["layer"] in {"micro", "auto", "full"}
    assert len(evidence) == 5  # evidence store untouched
