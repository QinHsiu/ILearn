"""Tests for MathTutorBench-style mistake location benchmark."""

from __future__ import annotations

from pathlib import Path

from ilearn.eval.mathtutorbench_tasks import (
    detect_first_error_step,
    load_mistake_location_fixtures,
    run_mistake_location_benchmark,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "eval" / "mistake_location_fixtures.json"


def test_mistake_location_fixtures_load():
    fixtures = load_mistake_location_fixtures(FIXTURES)
    assert len(fixtures) == 10


def test_detect_first_error_step_offline():
    fixtures = load_mistake_location_fixtures(FIXTURES)
    ml_01 = next(f for f in fixtures if f.id == "ml_01")
    assert detect_first_error_step(ml_01) == 2


def test_detect_first_error_step_all_correct():
    fixtures = load_mistake_location_fixtures(FIXTURES)
    ml_02 = next(f for f in fixtures if f.id == "ml_02")
    assert detect_first_error_step(ml_02) is None


def test_mistake_location_offline_perfect_on_gold():
    report = run_mistake_location_benchmark(FIXTURES, llm=None)
    assert report["total"] == 10
    assert report["first_error_acc"] >= 0.8
    assert report["step_f1"] >= 0.8
