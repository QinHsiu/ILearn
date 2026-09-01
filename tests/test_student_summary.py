from ilearn.core.audience_summary import build_student_summary, StudentSummary
from ilearn.core.schemas import (
    SessionState,
    StudentProfile,
    SessionPhase,
    LearningPlanReport,
    PlanDay,
)
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit


def test_build_student_summary_uses_metadata_when_present():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    session.metadata["student_summary"] = {
        "current_task": "巩固：小数乘小数",
        "completed_tasks": 2,
        "total_tasks": 5,
        "stars_earned": 5,
        "next_challenge": "挑战：运算律推广到小数",
        "narrative": "今天又进步啦，继续加油！",
    }
    s = build_student_summary(session)
    assert isinstance(s, StudentSummary)
    assert s.current_task == "巩固：小数乘小数"
    assert s.completed_tasks == 2
    assert s.total_tasks == 5
    assert s.stars_earned == 5
    assert s.next_challenge.startswith("挑战")
    assert s.narrative


def test_build_student_summary_formula_without_metadata():
    session = SessionState(
        session_id="plain-s",
        profile=StudentProfile(region="beijing", grade=5, age=11, nickname="小华"),
        phase=SessionPhase.PLAN,
        plan=LearningPlanReport(
            status="approved",
            goal="巩固小数乘法",
            days=[
                PlanDay(
                    day=1,
                    focus_knowledge_ids=["kp_a"],
                    tasks=["练习小数乘整数"],
                    minutes=20,
                )
            ],
            markdown="x",
        ),
        answers=[],
        metadata={"demo_weaknesses_resolved": 1},
    )
    s = build_student_summary(session)
    assert s.current_task == "巩固小数乘法"
    assert s.total_tasks == 1
    assert s.completed_tasks == 0
    assert s.stars_earned == 2  # 1*2 + 0
    assert "任务" in s.narrative
