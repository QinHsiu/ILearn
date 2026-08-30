"""Tests for graph cycle validator."""

from __future__ import annotations

from ilearn.core.graph_validator import GraphValidator


def test_detects_cycle():
    graph = {
        "a": {"prerequisites": ["b"]},
        "b": {"prerequisites": ["a"]},
    }
    cycles = GraphValidator.detect_circular_dependency(graph)
    assert cycles
    report = GraphValidator.validate_graph(graph)
    assert report["valid"] is False


def test_valid_dag():
    graph = {
        "a": {"prerequisites": []},
        "b": {"prerequisites": ["a"]},
        "c": {"prerequisites": ["b"]},
    }
    assert GraphValidator.detect_circular_dependency(graph) == []
    assert GraphValidator.validate_graph(graph)["valid"] is True
