"""P11 companion continuity + replan explain win-bar."""

from datetime import datetime, timedelta, timezone

from ilearn.core.companion_continuity import build_learner_continuity
from ilearn.core.replan_explain import build_replan_explanation
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    KnowledgeMastery,
    LearnerPortrait,
    LearningPlanReport,
    MasteryRecord,
    PortraitDimensions,
    SessionState,
    StudentProfile,
)


def _sess(sid: str, day_offset: int, weak: str, *, with_portrait: bool = False) -> SessionState:
    created = datetime.now(timezone.utc) - timedelta(days=day_offset)
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="q1",
                stem="x",
                type="fill",
                difficulty="easy",
                knowledge_ids=["kp"],
            )
        ],
        grade=5,
        curriculum_label="北京·人教",
        created_at=created,
    )
    portrait = None
    if with_portrait:
        portrait = LearnerPortrait(
            student_key="bj_g5",
            mastery_records={
                "kp": MasteryRecord(probe_mastery=0.3, practice_score=0.6),
            },
            knowledge_state={"kp": 0.3},
            dimensions=PortraitDimensions(
                emotional={"frustration": 0.45},
                behavioral={"hint_dependency": 0.5},
            ),
        )
    return SessionState(
        session_id=sid,
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        paper=paper,
        diagnosis=DiagnosisReport(
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp",
                    knowledge_name=weak,
                    score_rate=0.3,
                    level="weak",
                )
            ],
            curriculum_label="北京·人教",
            flags=["practice_probe_gap"] if with_portrait else [],
        ),
        portrait=portrait,
        metadata={
            "replan_explain": {
                "triggered": True,
                "reasons": ["挫败感偏高"],
            }
        }
        if with_portrait
        else {},
    )


def test_p11_continuity_streak_and_chain():
    sessions = [
        _sess("s0", 0, "小数乘法"),
        _sess("s1", 1, "小数意义"),
        _sess("s2", 2, "进位加法"),
    ]
    view = build_learner_continuity("小明", sessions)
    assert view.session_count == 3
    assert view.streak_days >= 2
    assert view.next_challenge == "小数乘法"
    assert len(view.seven_day_chain) == 7
    assert view.seven_day_chain[0].session_id == "s0"


def test_p11_portrait_snapshot_and_replan_explain():
    sessions = [_sess("s0", 0, "小数乘法", with_portrait=True)]
    view = build_learner_continuity("小明", sessions)
    assert view.portrait_snapshot is not None
    assert view.portrait_snapshot.frustration >= 0.4
    assert view.latest_replan_explain is not None
    assert view.latest_replan_explain.get("triggered") is True


def test_p11_replan_explanation_reasons():
    portrait = LearnerPortrait(
        student_key="x",
        dimensions=PortraitDimensions(
            emotional={"frustration": 0.5},
            behavioral={"hint_dependency": 0.5},
        ),
    )
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教",
        flags=["practice_probe_gap"],
        knowledge_mastery=[],
    )
    explain = build_replan_explanation(
        portrait=portrait,
        diagnosis=diagnosis,
        previous_plan=LearningPlanReport(goal="旧目标", markdown="a"),
        new_plan=LearningPlanReport(goal="新目标", markdown="b"),
    )
    assert explain.triggered is True
    assert len(explain.reasons) >= 2
    assert explain.previous_goal == "旧目标"
    assert explain.new_goal == "新目标"
