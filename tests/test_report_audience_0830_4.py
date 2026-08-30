"""Report includes audience summaries."""

from __future__ import annotations

from ilearn.core.report import render_full_report
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)


def test_report_includes_parent_teacher_sections():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=DiagnosisReport(
            curriculum_label="x",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="frac_mult", score_rate=0.2, level="weak"
                )
            ],
        ),
        metadata={
            "diagnosis_enrichment": {
                "weak_skills": ["frac_mult"],
                "parent_summary": "家长摘要测试",
                "teacher_summary": "教师摘要测试",
                "error_attribution": {
                    "counts": {"calc_error": 2},
                    "top_tags": ["calc_error"],
                },
            }
        },
    )
    md = render_full_report(session)
    assert "家长可读摘要" in md
    assert "家长摘要测试" in md
    assert "教师可读摘要" in md
    assert "错误类型归因" in md
    assert "calc_error" in md
