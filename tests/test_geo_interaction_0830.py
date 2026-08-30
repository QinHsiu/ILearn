"""Tests for geometry interaction trajectory analysis."""

from __future__ import annotations

from ilearn.agents.practice import PracticeAgent


def test_confident_short_path():
    agent = PracticeAgent()
    log = [
        {"type": "drag_point", "position": [1.0, 2.0]},
        {"type": "drag_point", "position": [1.05, 2.0]},
    ]
    out = agent.analyze_geo_interaction(log, {"x": 1.0, "y": 2.0})
    assert out["status"] == "confident"


def test_explored_long_path():
    agent = PracticeAgent()
    log = [
        {"type": "drag_point", "position": [0.0, 0.0]},
        {"type": "drag_point", "position": [3.0, 0.0]},
        {"type": "drag_point", "position": [3.0, 3.0]},
        {"type": "drag_point", "position": [1.0, 2.0]},
    ]
    out = agent.analyze_geo_interaction(log, {"x": 1.0, "y": 2.0})
    assert out["status"] == "explored"


def test_struggling_many_attempts():
    agent = PracticeAgent()
    log = [
        {"type": "drag_point", "position": [float(i), 0.0]} for i in range(7)
    ]
    out = agent.analyze_geo_interaction(log, {"x": 10.0, "y": 10.0})
    assert out["status"] == "struggling"


def test_empty_log():
    agent = PracticeAgent()
    out = agent.analyze_geo_interaction([], {"x": 1.0, "y": 2.0})
    assert out["status"] == "empty"
