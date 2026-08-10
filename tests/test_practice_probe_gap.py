from ilearn.core.diagnosis import Diagnoser
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    LearnerPortrait,
    MasteryRecord,
    StudentProfile,
)
from ilearn.eval.gap import compute_gap, gap_exceeds, gap_flag
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_gap_exceeds_when_practice_exceeds_probe():
    assert gap_exceeds(practice=0.9, probe=0.4, threshold=0.25) is True
    assert gap_exceeds(practice=0.5, probe=0.4, threshold=0.25) is False


def test_compute_gap():
    assert compute_gap(0.9, 0.4) == 0.5


def test_gap_flag_from_portrait():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.9,
        probe_mastery=0.4,
    )
    assert gap_flag(portrait) == ["practice_probe_gap"]


def test_diagnosis_report_includes_gap_flag():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.9,
        probe_mastery=0.4,
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
    report = Diagnoser(PilotBeijingRenjiaoProvider(PILOT)).diagnose(
        profile, paper, grades, portrait=portrait
    )
    assert "practice_probe_gap" in report.flags
