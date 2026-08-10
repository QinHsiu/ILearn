from pathlib import Path

from ilearn.core.planning import Planner
from ilearn.core.schemas import (
    DiagnosisReport,
    Intervention,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _sample_diagnosis() -> DiagnosisReport:
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
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_add_same",
                title="同分母分数加法",
                why="得分率 0%",
                what_to_fix_first="概念理解",
                priority=1,
            ),
        ],
    )


def test_plan_markdown_contains_three_part_intervention_headings():
    planner = Planner(PilotBeijingRenjiaoProvider(ROOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    plan = planner.plan(profile, _sample_diagnosis())
    for heading in ("### 当前认知", "### 预测难点", "### 教学方案"):
        assert heading in plan.markdown


def test_three_part_intervention_uses_top_intervention_and_error_tag():
    planner = Planner(PilotBeijingRenjiaoProvider(ROOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    plan = planner.plan(profile, _sample_diagnosis())
    assert "同分母分数加法" in plan.markdown
    assert "概念缺口" in plan.markdown or "概念理解" in plan.markdown
