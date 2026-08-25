"""Tests for KnowledgeGraph prerequisite lookups."""

from __future__ import annotations

from pathlib import Path

from ilearn.core.knowledge_graph import KnowledgeGraph


def test_get_prerequisites_known_node(tmp_path: Path):
    path = tmp_path / "knowledge_graph.json"
    path.write_text(
        '{"frac_mult": {"prerequisites": ["frac_add_same"], "related": [], "grade": 5}}',
        encoding="utf-8",
    )
    graph = KnowledgeGraph(path)
    assert graph.get_prerequisites("frac_mult") == ["frac_add_same"]
    assert graph.get_grade_for_skill("frac_mult") == 5
    assert graph.get_all_related("frac_mult") == {"frac_add_same"}


def test_unknown_id_is_fail_soft(tmp_path: Path):
    path = tmp_path / "knowledge_graph.json"
    path.write_text("{}", encoding="utf-8")
    graph = KnowledgeGraph(path)
    assert graph.get_prerequisites("no_such_kp") == []
    assert graph.get_all_related("no_such_kp") == set()
    assert graph.get_grade_for_skill("no_such_kp") == 0


def test_default_repo_graph_loads():
    graph = KnowledgeGraph()
    assert "frac_add_same" in graph.get_prerequisites("frac_mult")
