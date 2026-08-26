from pathlib import Path

from ilearn.data.importers.rcae_graph import parse_rcae, to_ilearn_graph, to_ilearn_knowledge
from ilearn.data.kp_ids import load_alias_map

FIX = Path(__file__).parent / "fixtures" / "rcae_tiny.json"
ALIAS = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"


def test_parse_rcae_returns_nodes_and_edges():
    nodes, edges = parse_rcae(FIX)
    assert len(nodes) >= 3
    assert len(edges) >= 1


def test_to_ilearn_graph_prerequisite_chain():
    nodes, edges = parse_rcae(FIX)
    alias = load_alias_map(ALIAS)
    graph = to_ilearn_graph(nodes, edges, alias, grades=(4, 5, 6))
    assert "frac_mult" in graph or any("prerequisites" in v for v in graph.values())
    for node in graph.values():
        assert "grade" in node
        assert isinstance(node["prerequisites"], list)
        assert isinstance(node["related"], list)
