from pathlib import Path

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    KnowledgeEvidence,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_intervention_includes_evidence_ids():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    evidence = [
        KnowledgeEvidence(
            session_id="s1",
            item_id="q1",
            knowledge_id="frac_add_same",
            lane="probe",
            correct=False,
            error_tag="concept_gap",
        ),
        KnowledgeEvidence(
            session_id="s1",
            item_id="q2",
            knowledge_id="frac_add_same",
            lane="probe",
            correct=False,
            error_tag="calc_error",
        ),
    ]
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="i1",
                stem="q1",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_add_same"],
                answer_key="A",
            ),
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    grades = [
        GradeResult(
            item_id="i1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
            lane="probe",
        ),
    ]
    profile = StudentProfile(region="北京", grade=5, age=11)
    report = Diagnoser(curriculum).diagnose(
        profile, paper, grades, evidence=evidence
    )
    assert report.evidence_refs == [ev.evidence_id for ev in evidence]
    iv = report.interventions[0]
    assert iv.knowledge_id == "frac_add_same"
    assert set(iv.evidence_ids) == {ev.evidence_id for ev in evidence}


def test_intervention_evidence_ids_empty_without_evidence():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="i1",
                stem="q1",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_add_same"],
                answer_key="A",
            ),
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    grades = [
        GradeResult(
            item_id="i1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
        ),
    ]
    profile = StudentProfile(region="北京", grade=5, age=11)
    report = Diagnoser(curriculum).diagnose(profile, paper, grades)
    assert report.evidence_refs == []
    assert report.interventions[0].evidence_ids == []
