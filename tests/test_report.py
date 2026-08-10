from pathlib import Path

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.planning import Planner
from ilearn.core.report import render_full_report
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_render_full_report_includes_sections():
    profile = StudentProfile(region="上海", grade=5, age=11)
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="r1",
                stem="r1",
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
            item_id="r1",
            final_correct=False,
            knowledge_ids=["frac_add_same"],
            error_tags=["concept_gap"],
        ),
    ]
    curriculum = PilotBeijingRenjiaoProvider(ROOT)
    diagnosis = Diagnoser(curriculum).diagnose(profile, paper, grades)
    plan = Planner(curriculum).plan(profile, diagnosis)
    session = SessionState(
        session_id="test-session",
        profile=profile,
        paper=paper,
        grades=grades,
        diagnosis=diagnosis,
        plan=plan,
    )
    md = render_full_report(session)
    assert "学情" in md
    assert "计划" in md or "学习计划" in md
    assert "北京" in md
    assert diagnosis.region_mismatch_disclaimer
    assert diagnosis.region_mismatch_disclaimer.split("。")[0] in md or "地区" in md
