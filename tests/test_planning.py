from pathlib import Path

import pytest

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.planning import Planner
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    Intervention,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture
def planner():
    return Planner(PilotBeijingRenjiaoProvider(ROOT))


@pytest.fixture
def profile():
    return StudentProfile(region="北京", grade=5, age=11)


@pytest.fixture
def sample_diagnosis():
    return DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_add_same",
                score_rate=0.0,
                level="weak",
                item_ids=["i1", "i2"],
                error_tag_counts={"concept_gap": 2},
            ),
            KnowledgeMastery(
                knowledge_id="dec_mult",
                score_rate=0.5,
                level="unstable",
                item_ids=["i3"],
                error_tag_counts={"calc_error": 1},
            ),
            KnowledgeMastery(
                knowledge_id="frac_mult",
                score_rate=1.0,
                level="mastered",
                item_ids=["i4"],
            ),
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_add_same",
                title="同分母分数加法",
                why="得分率 0%",
                what_to_fix_first="概念理解",
                priority=1,
            ),
            Intervention(
                knowledge_id="dec_mult",
                title="小数乘法",
                why="得分率 50%",
                what_to_fix_first="计算准确性",
                priority=2,
            ),
        ],
        ability_scores={"logic": 45.0, "mental_math": 60.0},
    )


def test_plan_links_weak_knowledge(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis)
    weak = {i.knowledge_id for i in sample_diagnosis.interventions}
    linked = {kid for day in plan.days for kid in day.focus_knowledge_ids}
    assert weak & linked


def test_default_7_days(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis)
    assert len(plan.days) == 7


def test_daily_minutes_default_40(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis)
    assert all(day.minutes == 40 for day in plan.days)


def test_custom_daily_minutes(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis, daily_minutes=30)
    assert all(day.minutes == 30 for day in plan.days)


def test_plan_prioritizes_weakest_first(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis)
    first_focus = plan.days[0].focus_knowledge_ids
    assert "frac_add_same" in first_focus


def test_plan_has_goal_milestones_and_markdown(planner, profile, sample_diagnosis):
    plan = planner.plan(profile, sample_diagnosis)
    assert plan.goal
    assert plan.milestones
    assert plan.markdown
    assert "计划" in plan.markdown or "学习" in plan.markdown
    assert plan.disclaimer


def test_plan_max_14_days(planner, profile):
    many = [
        Intervention(
            knowledge_id=f"k{i}",
            title=f"知识点{i}",
            why="weak",
            what_to_fix_first="review",
            priority=i,
        )
        for i in range(1, 16)
    ]
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        interventions=many,
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id=f"k{i}",
                score_rate=0.1,
                level="weak",
                item_ids=[f"i{i}"],
            )
            for i in range(1, 16)
        ],
    )
    plan = planner.plan(profile, diagnosis, plan_days=14)
    assert len(plan.days) == 14


def test_end_to_end_with_diagnoser(planner, profile):
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="e1",
                stem="e1",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_add_same"],
                answer_key="A",
            ),
            AssessmentItem(
                id="e2",
                stem="e2",
                type="fill",
                difficulty="easy",
                knowledge_ids=["dec_mult"],
                answer_key="1",
            ),
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    grades = [
        GradeResult(item_id="e1", final_correct=False, knowledge_ids=["frac_add_same"], error_tags=["concept_gap"]),
        GradeResult(item_id="e2", final_correct=True, knowledge_ids=["dec_mult"]),
    ]
    diagnosis = Diagnoser(PilotBeijingRenjiaoProvider(ROOT)).diagnose(profile, paper, grades)
    plan = planner.plan(profile, diagnosis)
    assert plan.days
    assert plan.markdown
