"""Tests for SM-2 spaced review scheduling."""

from __future__ import annotations

from datetime import date, timedelta

from ilearn.core.review import ReviewState, due_knowledge_ids, sm2_update
from ilearn.core.schemas import LearnerPortrait


def test_sm2_increases_interval_on_good_quality():
    state = ReviewState()
    updated = sm2_update(state, quality=4)
    assert updated.interval_days >= 1
    assert updated.repetitions == 1
    assert updated.due_date == date.today() + timedelta(days=1)


def test_sm2_resets_on_poor_quality():
    state = ReviewState(repetitions=3, interval_days=10, ease_factor=2.5)
    updated = sm2_update(state, quality=2)
    assert updated.repetitions == 0
    assert updated.interval_days == 1
    assert updated.ease_factor == 2.3


def test_sm2_second_repetition_six_day_interval():
    state = ReviewState(repetitions=1, interval_days=1, ease_factor=2.5)
    updated = sm2_update(state, quality=4)
    assert updated.repetitions == 2
    assert updated.interval_days == 6


def test_due_knowledge_ids_returns_overdue():
    today = date(2026, 8, 10)
    portrait = LearnerPortrait(
        student_key="bj_g5",
        review_states={
            "frac_add_same": ReviewState(due_date=date(2026, 8, 9)),
            "dec_mult": ReviewState(due_date=date(2026, 8, 11)),
            "frac_mult": ReviewState(due_date=None),
        },
    )
    due = due_knowledge_ids(portrait, today)
    assert due == ["frac_add_same"]


def test_planner_prepends_review_tasks():
    from ilearn.core.planning import Planner
    from ilearn.core.schemas import (
        DiagnosisReport,
        Intervention,
        KnowledgeMastery,
        StudentProfile,
    )
    from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
    from pathlib import Path

    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    planner = Planner(PilotBeijingRenjiaoProvider(pilot))
    portrait = LearnerPortrait(
        student_key="bj_g5",
        review_states={
            "dec_mult": ReviewState(due_date=date.today()),
        },
    )
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_add_same",
                score_rate=0.2,
                level="weak",
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
    plan = planner.plan(
        StudentProfile(region="北京", grade=5, age=11),
        diagnosis,
        portrait=portrait,
    )
    day1_tasks = plan.days[0].tasks
    assert any("复习" in task for task in day1_tasks)
    assert "dec_mult" in plan.days[0].focus_knowledge_ids or any(
        "小数" in task for task in day1_tasks
    )
