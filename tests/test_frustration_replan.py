from ilearn.core.planning import Planner
from ilearn.core.replan import replan_adjustments, should_replan
from ilearn.core.schemas import (
    DiagnosisReport,
    Intervention,
    KnowledgeMastery,
    LearnerPortrait,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_should_replan_on_high_frustration():
    portrait = LearnerPortrait(student_key="x")
    portrait.dimensions.emotional["frustration"] = 0.5
    assert should_replan(portrait, DiagnosisReport(curriculum_label="x")) is True


def test_should_replan_on_hint_dependency():
    portrait = LearnerPortrait(student_key="x")
    portrait.dimensions.behavioral["hint_dependency"] = 0.5
    assert should_replan(portrait, DiagnosisReport(curriculum_label="x")) is True


def test_should_replan_on_practice_probe_gap_flag():
    portrait = LearnerPortrait(student_key="x")
    diagnosis = DiagnosisReport(
        curriculum_label="x",
        flags=["practice_probe_gap"],
    )
    assert should_replan(portrait, diagnosis) is True


def test_should_not_replan_when_calm():
    portrait = LearnerPortrait(student_key="x")
    assert should_replan(portrait, DiagnosisReport(curriculum_label="x")) is False


def test_replan_adjustments_returns_confidence_task():
    adjustments = replan_adjustments(DiagnosisReport(curriculum_label="x"))
    assert adjustments["easier_focus"] is True
    assert "已掌握" in adjustments["confidence_task"]


def test_replan_plan_includes_confidence_rebuild():
    planner = Planner(PilotBeijingRenjiaoProvider(ROOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_add_same",
                score_rate=0.0,
                level="weak",
                item_ids=["i1"],
            ),
            KnowledgeMastery(
                knowledge_id="dec_mult",
                score_rate=0.4,
                level="weak",
                item_ids=["i2"],
            ),
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_add_same",
                title="同分母分数加法",
                why="weak",
                what_to_fix_first="概念",
                priority=1,
            ),
            Intervention(
                knowledge_id="dec_mult",
                title="小数乘法",
                why="weak",
                what_to_fix_first="计算",
                priority=2,
            ),
        ],
    )
    portrait = LearnerPortrait(student_key="x")
    portrait.dimensions.emotional["frustration"] = 0.5
    plan = planner.plan(profile, diagnosis, portrait=portrait)
    day1_tasks = plan.days[0].tasks
    assert any("信心重建" in task for task in day1_tasks)
    assert plan.days[0].focus_knowledge_ids[0] == "dec_mult"
