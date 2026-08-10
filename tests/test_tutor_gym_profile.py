"""Tests for TutorGym-style step completeness benchmark."""

from __future__ import annotations

from pathlib import Path

from ilearn.eval.tutor_gym_profile import (
    load_completeness_profiles,
    run_completeness_benchmark,
    score_profile,
)

PROFILES = Path(__file__).resolve().parents[1] / "data" / "eval" / "step_completeness_profiles.json"


def test_completeness_penalizes_missing_steps():
    report = run_completeness_benchmark(PROFILES, llm=None)
    assert "completeness" in report
    assert report["total"] >= 5
    assert report["completeness"] < 1.0


def test_score_profile_full_submission():
    profiles = load_completeness_profiles(PROFILES)
    full = next(p for p in profiles if p.item_id == "tg_02")
    metrics = score_profile(full)
    assert metrics["completeness"] == 1.0
    assert metrics["correctness"] == 1.0
    assert metrics["avg_step_score"] == 1.0


def test_score_profile_partial_submission():
    profiles = load_completeness_profiles(PROFILES)
    partial = next(p for p in profiles if p.item_id == "tg_01")
    metrics = score_profile(partial)
    assert metrics["completeness"] == 2 / 3
    assert metrics["correctness"] == 0.0
