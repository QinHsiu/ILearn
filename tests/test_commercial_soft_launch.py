from ilearn.core.parent_action_summary import build_parent_action_summary
from ilearn.core.tier_suggest import classify_tiers
from ilearn.agents.tutor import TutorAgent
from ilearn.core.schemas import AssessmentItem


def test_parent_action_summary_has_executable_actions():
    summary = build_parent_action_summary(
        child_name="小明",
        current_mastery=0.62,
        mastery_change=0.08,
        weak_skills=["小数意义"],
    )
    assert "小明" in summary.headline
    assert summary.actions
    assert any("5 分钟" in a or "5分钟" in a for a in summary.actions)


def test_tier_suggest_three_buckets():
    tiers = classify_tiers(
        [
            {"name": "A", "avg_mastery": 0.2},
            {"name": "B", "avg_mastery": 0.5},
            {"name": "C", "avg_mastery": 0.9},
        ],
        weak_topic="小数乘法",
    )
    assert tiers.basic == ["A"]
    assert tiers.advanced == ["B"]
    assert tiers.challenge == ["C"]
    assert "小数乘法" in tiers.next_step


def test_tutor_soft_exit_redacts_answer_and_sets_action():
    item = AssessmentItem(
        id="q1",
        stem="1.2×3=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["kp1"],
        answer_key="3.6",
        rubric_steps=["对齐小数位", "相乘", "点小数点"],
    )
    turn = TutorAgent().step("retry", "还是不会", item, "calc_error")
    assert turn.phase == "explain"
    assert turn.action == "suggest_review"
    assert "3.6" not in turn.message
    done = TutorAgent().step("explain", "好的", item, "calc_error")
    assert done.action == "suggest_review"
    assert "最终答案" in done.message or "不" in done.message
