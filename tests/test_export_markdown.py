"""Tests for assessment-review export markdown (report.txt-shaped)."""

from __future__ import annotations

from ilearn.core.export_markdown import render_assessment_review_markdown
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    HintInteraction,
    KnowledgeMastery,
    SessionState,
    StudentAnswer,
    StudentProfile,
)


def _session() -> SessionState:
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="小明")
    items = [
        AssessmentItem(
            id="q1",
            stem="计算 1+1",
            type="fill",
            difficulty="easy",
            knowledge_ids=["add"],
            answer_key="2",
        ),
        AssessmentItem(
            id="q2",
            stem="计算 3×4",
            type="fill",
            difficulty="easy",
            knowledge_ids=["mul"],
            answer_key="12",
        ),
    ]
    paper = AssessmentPaper(items=items, grade=5, curriculum_label="北京·人教·小学数学")
    answers = [
        StudentAnswer(item_id="q1", answer_text="2"),
        StudentAnswer(item_id="q2", answer_text="11"),
    ]
    grades = [
        GradeResult(item_id="q1", final_correct=True, knowledge_ids=["add"]),
        GradeResult(item_id="q2", final_correct=False, knowledge_ids=["mul"]),
    ]
    diagnosis = DiagnosisReport(
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="add", score_rate=1.0, level="mastered", item_ids=["q1"]
            ),
            KnowledgeMastery(
                knowledge_id="mul", score_rate=0.0, level="weak", item_ids=["q2"]
            ),
        ],
        ability_scores={"logic": 60.0},
        curriculum_label="北京·人教·小学数学",
        interventions=[],
    )
    return SessionState(
        session_id="export-test",
        profile=profile,
        paper=paper,
        answers=answers,
        grades=grades,
        diagnosis=diagnosis,
        hint_interactions={
            "q2": [
                HintInteraction(
                    item_id="q2",
                    turn=1,
                    user_input="不会",
                    ai_hint="先想乘法口诀",
                )
            ]
        },
    )


def test_assessment_review_includes_cover_accuracy_and_answers():
    md = render_assessment_review_markdown(_session())
    assert "个性化学习报告" in md or "做题复盘" in md
    assert "小明" in md
    assert "50%" in md or "50.0%" in md
    assert "计算 1+1" in md
    assert "计算 3×4" in md
    assert "你的答案" in md
    assert "正确答案" in md
    assert "12" in md


def test_assessment_review_includes_hint_summary():
    md = render_assessment_review_markdown(_session())
    assert "提示" in md
    assert "1" in md


def test_assessment_review_requires_paper_and_grades():
    session = SessionState(
        session_id="empty",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    try:
        render_assessment_review_markdown(session)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "测评" in str(exc) or "批改" in str(exc)
