from ilearn.core.audience_summary import (
    build_parent_summary,
    build_teacher_summary,
)
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit
from ilearn.core.schemas import SessionState, StudentProfile, SessionPhase


def test_build_teacher_summary_from_demo_seed():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    s = build_teacher_summary(session)
    assert s.class_name == "demo_class_5a"
    assert s.student_count == 35
    assert s.avg_mastery == 0.62
    assert len(s.top_weaknesses) >= 2
    assert s.top_weaknesses[0].affected_students >= 1
    assert any(row.name == (session.profile.nickname or "学生") for row in s.need_intervention_students)
    assert len(s.need_intervention_students) >= 2  # demo peers
    assert 0 < s.auto_graded_rate <= 1
    assert s.estimated_time_saved_minutes == 33.5
    assert s.narrative


def test_build_parent_summary_from_demo_seed():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    s = build_parent_summary(session)
    assert s.child_name == "小明"
    assert abs(s.current_mastery - 0.78) < 1e-6
    assert abs(s.mastery_change - 0.18) < 1e-6
    assert s.weak_skills
    assert s.learning_phase == "plan"
    assert s.daily_practice_tips
    assert s.next_milestone
    assert s.narrative


def test_build_teacher_summary_non_demo_no_synthetic_peers():
    session = SessionState(
        session_id="plain-1",
        profile=StudentProfile(region="beijing", grade=5, age=11, nickname="小华"),
        phase=SessionPhase.IDLE,
        metadata={},
    )
    s = build_teacher_summary(session)
    assert s.student_count == 1
    assert s.class_name == "当前班级"
    assert len(s.need_intervention_students) == 1
