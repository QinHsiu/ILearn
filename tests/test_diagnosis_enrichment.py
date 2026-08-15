from pathlib import Path

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_diagnoser_adds_solo_and_rule_flags():
    diagnoser = Diagnoser(PilotBeijingRenjiaoProvider(PILOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="q1",
                stem="1",
                type="fill",
                difficulty="easy",
                answer_key="1",
                knowledge_ids=["frac_add_same"],
            )
        ],
        grade=5,
        curriculum_label="pilot",
    )
    grades = [
        GradeResult(
            item_id="q1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
        )
    ]
    report = diagnoser.diagnose(profile, paper, grades)
    assert any(f.startswith("solo:") for f in report.flags)
    assert "rule:concept_gap" in report.flags
    assert report.interventions
    assert "SOLO" in report.interventions[0].why or "规则" in report.interventions[0].why
