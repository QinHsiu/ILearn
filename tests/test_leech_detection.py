from pathlib import Path

from ilearn.core.diagnosis import Diagnoser, PortraitUpdater, is_leech
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    KnowledgeEvidence,
    LearnerPortrait,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _three_probe_failures() -> list[KnowledgeEvidence]:
    return [
        KnowledgeEvidence(
            session_id="s1",
            item_id=f"q{i}",
            knowledge_id="frac_add_same",
            lane="probe",
            correct=False,
            error_tag="concept_gap",
        )
        for i in range(3)
    ]


def test_is_leech_after_three_incorrect_probe_evidence():
    portrait = LearnerPortrait(student_key="bj_g5")
    evidence = _three_probe_failures()
    PortraitUpdater.update(
        portrait,
        [],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
        evidence=evidence,
    )
    assert is_leech(portrait, "frac_add_same", evidence=evidence) is True
    assert is_leech(portrait, "frac_add_same", evidence=evidence[:2], threshold=3) is False


def test_three_probe_failures_mark_leech_on_intervention():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    portrait = LearnerPortrait(student_key="bj_g5")
    evidence = _three_probe_failures()
    PortraitUpdater.update(
        portrait,
        [],
        session_id="s1",
        curriculum=curriculum,
        grade=5,
        evidence=evidence,
    )
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
            AssessmentItem(
                id="i2",
                stem="q2",
                type="choice",
                difficulty="easy",
                knowledge_ids=["dec_mult"],
                answer_key="B",
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
        GradeResult(
            item_id="i2",
            final_correct=True,
            knowledge_ids=["dec_mult"],
            lane="probe",
        ),
    ]
    profile = StudentProfile(region="北京", grade=5, age=11)
    report = Diagnoser(curriculum).diagnose(
        profile, paper, grades, portrait=portrait, evidence=evidence
    )
    leech_iv = next(
        (iv for iv in report.interventions if iv.knowledge_id == "frac_add_same"),
        None,
    )
    assert leech_iv is not None
    assert leech_iv.leech is True
    assert leech_iv.priority == 1


def test_leech_boosts_priority_over_weaker_non_leech():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    portrait = LearnerPortrait(student_key="bj_g5")
    leech_evidence = _three_probe_failures()
    PortraitUpdater.update(
        portrait,
        [],
        session_id="s1",
        curriculum=curriculum,
        grade=5,
        evidence=leech_evidence,
    )
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
            AssessmentItem(
                id="i2",
                stem="q2",
                type="choice",
                difficulty="easy",
                knowledge_ids=["simple_eq"],
                answer_key="B",
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
        GradeResult(
            item_id="i2",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["simple_eq"],
            lane="probe",
        ),
    ]
    profile = StudentProfile(region="北京", grade=5, age=11)
    report = Diagnoser(curriculum).diagnose(
        profile, paper, grades, portrait=portrait, evidence=leech_evidence
    )
    assert report.interventions[0].knowledge_id == "frac_add_same"
    assert report.interventions[0].leech is True
