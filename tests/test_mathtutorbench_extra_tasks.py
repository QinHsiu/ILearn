"""Tests for mistake_correction and scaffolding MathTutorBench-style benchmarks."""

from __future__ import annotations

from pathlib import Path

from ilearn.eval.mathtutorbench_tasks import (
    run_mistake_correction_benchmark,
    run_scaffolding_benchmark,
)


def test_mistake_correction_offline_acc():
    path = (
        Path(__file__).resolve().parents[1]
        / "data/eval/mistake_correction_fixtures.json"
    )
    report = run_mistake_correction_benchmark(path, llm=None)
    assert report["total"] >= 5
    assert report["correction_acc"] >= 0.8


def test_scaffolding_offline_hint_match():
    path = (
        Path(__file__).resolve().parents[1] / "data/eval/scaffolding_fixtures.json"
    )
    report = run_scaffolding_benchmark(path, llm=None)
    assert report["total"] >= 5
    assert report["hint_level_match"] >= 0.8
