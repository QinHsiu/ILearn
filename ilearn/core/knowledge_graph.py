"""Knowledge prerequisite graph for cold-start diagnosis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ilearn.core.logging_utils import get_logger

_LOG = get_logger("ilearn.knowledge_graph")
_WARNED_CYCLE_PATHS: set[str] = set()

_DEFAULT_GRAPH: dict[str, Any] = {
    "mult_3digit": {"prerequisites": [], "related": ["rect_area"], "grade": 4},
    "rect_area": {
        "prerequisites": ["mult_3digit"],
        "related": ["parallel_perp"],
        "grade": 4,
    },
    "angle_measure": {"prerequisites": [], "related": ["parallel_perp"], "grade": 4},
    "parallel_perp": {
        "prerequisites": ["angle_measure"],
        "related": ["rect_area"],
        "grade": 4,
    },
    "dec_mult": {
        "prerequisites": ["mult_3digit"],
        "related": ["frac_mult"],
        "grade": 5,
    },
    "frac_add_same": {
        "prerequisites": [],
        "related": ["frac_mult", "frac_div"],
        "grade": 5,
    },
    "frac_mult": {
        "prerequisites": ["frac_add_same"],
        "related": ["frac_div", "dec_mult"],
        "grade": 5,
    },
    "simple_eq": {
        "prerequisites": ["dec_mult"],
        "related": ["frac_mult"],
        "grade": 5,
    },
    "frac_div": {
        "prerequisites": ["frac_mult"],
        "related": ["ratio"],
        "grade": 6,
    },
    "ratio": {"prerequisites": ["frac_div"], "related": ["percent"], "grade": 6},
    "circle_area": {
        "prerequisites": ["rect_area"],
        "related": ["percent"],
        "grade": 6,
    },
    "percent": {"prerequisites": ["ratio"], "related": ["frac_div"], "grade": 6},
    "factors": {
        "prerequisites": ["mult_3digit"],
        "related": ["frac_div"],
        "grade": 6,
    },
}


class KnowledgeGraph:
    """Knowledge point graph for prerequisite and related lookups."""

    def __init__(
        self,
        graph_path: str | Path | None = None,
        *,
        strict_cycles: bool = False,
    ) -> None:
        if graph_path is None:
            root = Path(__file__).resolve().parents[2]
            graph_path = root / "data" / "knowledge_graph.json"
        self.graph_path = Path(graph_path)
        self.strict_cycles = strict_cycles
        self.cycle_count = 0
        self.graph = self._load_graph()

    def _load_graph(self) -> dict[str, Any]:
        if self.graph_path.exists():
            from ilearn.core.cache import load_json_cached

            graph = load_json_cached(self.graph_path)
        else:
            graph = json.loads(json.dumps(_DEFAULT_GRAPH))
        self._check_cycles(graph)
        return graph

    def _check_cycles(self, graph: dict[str, Any]) -> None:
        from ilearn.core.graph_validator import GraphValidator

        shaped: dict[str, dict[str, Any]] = {}
        for key, value in graph.items():
            if isinstance(value, dict):
                shaped[str(key)] = {
                    "prerequisites": list(value.get("prerequisites") or [])
                }
        cycles = GraphValidator.detect_circular_dependency(shaped)
        self.cycle_count = len(cycles)
        if not cycles:
            return
        # Truncate for logs / errors — full pilot graph can have huge cycle lists.
        preview = cycles[:3]
        msg = (
            f"knowledge graph has {len(cycles)} circular dependencies "
            f"(showing up to 3): {preview}"
        )
        if self.strict_cycles:
            raise ValueError(msg)
        path_key = str(self.graph_path.resolve()) if self.graph_path else "<memory>"
        if path_key not in _WARNED_CYCLE_PATHS:
            _WARNED_CYCLE_PATHS.add(path_key)
            _LOG.warning(
                "%s — continuing (strict_cycles=False; data cleanup pending)", msg
            )

    def get_prerequisites(self, knowledge_point: str) -> list[str]:
        return list(self.graph.get(knowledge_point, {}).get("prerequisites", []))

    def get_all_related(self, knowledge_point: str) -> set[str]:
        node = self.graph.get(knowledge_point, {})
        return set(node.get("prerequisites", []) + node.get("related", []))

    def get_grade_for_skill(self, knowledge_point: str) -> int:
        return int(self.graph.get(knowledge_point, {}).get("grade", 0))
