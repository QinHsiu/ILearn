from ilearn.core.planning import Planner, resolve_kc_type, task_for_kc
from ilearn.core.schemas import KnowledgeNode, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_task_for_kc_fact_wording():
    text = task_for_kc("fact", "同分母分数加法")
    assert "检索练习" in text
    assert "同分母分数加法" in text
    assert "关键结论" in text


def test_task_for_kc_skill_wording():
    text = task_for_kc("skill", "小数乘法")
    assert "变式练习" in text
    assert "小数乘法" in text
    assert "同类题" in text


def test_task_for_kc_principle_wording():
    text = task_for_kc("principle", "分数意义")
    assert "解释为什么" in text
    assert "分数意义" in text


def test_task_for_kc_unknown_defaults_to_skill():
    text = task_for_kc("unknown_type", "任意知识点")
    assert "变式练习" in text


def test_resolve_kc_type_from_explicit_field():
    node = KnowledgeNode(
        id="k1", grade=5, name="测试", ability_tags=["logic"], kc_type="principle"
    )
    assert resolve_kc_type(node) == "principle"


def test_resolve_kc_type_from_memory_tag():
    node = KnowledgeNode(id="k1", grade=5, name="测试", ability_tags=["记忆", "logic"])
    assert resolve_kc_type(node) == "fact"


def test_resolve_kc_type_from_understanding_tag():
    node = KnowledgeNode(id="k1", grade=5, name="测试", ability_tags=["理解"])
    assert resolve_kc_type(node) == "principle"


def test_resolve_kc_type_defaults_to_skill():
    node = KnowledgeNode(id="k1", grade=5, name="测试", ability_tags=["mental_math"])
    assert resolve_kc_type(node) == "skill"


def test_planner_day_tasks_use_kc_wording():
    planner = Planner(PilotBeijingRenjiaoProvider(PILOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    from ilearn.core.schemas import DiagnosisReport, Intervention, KnowledgeMastery

    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_add_same", score_rate=0.2, level="weak"
            ),
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_add_same",
                title="同分母分数加法",
                why="weak",
                what_to_fix_first="review",
                priority=1,
            ),
        ],
    )
    plan = planner.plan(profile, diagnosis)
    day1_tasks = plan.days[0].tasks
    assert any("变式练习" in t or "检索练习" in t or "解释为什么" in t for t in day1_tasks)
