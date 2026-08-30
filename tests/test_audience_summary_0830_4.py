"""Tests for audience summaries and error attribution."""

from __future__ import annotations

from ilearn.core.audience_summary import (
    aggregate_error_attribution,
    generate_audience_summary,
)
from ilearn.core.schemas import DiagnosisReport, GradeResult, KnowledgeMastery


def test_parent_summary_with_weak_skills():
    diagnosis = DiagnosisReport(
        curriculum_label="x",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="frac_mult", score_rate=0.2, level="weak")
        ],
    )
    text = generate_audience_summary(
        diagnosis,
        {"weak_skills": ["frac_mult"], "error_attribution": {"top_tags": ["calc_error"]}},
        audience="parent",
    )
    assert "frac_mult" in text
    assert "计算" in text


def test_aggregate_error_attribution():
    grades = [
        GradeResult(
            item_id="a",
            final_correct=False,
            error_tags=["calc_error"],
            knowledge_ids=["frac_mult"],
        ),
        GradeResult(
            item_id="b",
            final_correct=False,
            error_tags=["calc_error", "misread"],
            knowledge_ids=["frac_mult"],
        ),
        GradeResult(
            item_id="c",
            final_correct=True,
            error_tags=[],
            knowledge_ids=["frac_mult"],
        ),
    ]
    out = aggregate_error_attribution(grades)
    assert out["wrong_count"] == 2
    assert out["counts"]["calc_error"] == 2
    assert out["top_tags"][0] == "calc_error"
