"""Tests for learning style inference."""

from __future__ import annotations

from ilearn.core.learning_style import LearningStyleInferer


def test_visual_bias_from_diagrams():
    style = LearningStyleInferer().infer(
        {
            "diagram_expand_count": 8,
            "total_questions": 10,
            "audio_play_count": 0,
            "avg_response_time": 20,
            "visual_question_correct": 5,
            "visual_question_total": 5,
        }
    )
    assert style == "visual"


def test_posterior_sums_to_one():
    post = LearningStyleInferer().posterior({"total_questions": 1})
    assert abs(sum(post.values()) - 1.0) < 1e-6
