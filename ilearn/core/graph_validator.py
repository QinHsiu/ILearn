"""Prerequisite graph cycle detection and validation reports."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class GraphValidator:
    """Validate prerequisite graphs for cycles and basic health."""

    @staticmethod
    def detect_circular_dependency(graph: dict[str, dict[str, Any]]) -> list[list[str]]:
        """Return list of cycle paths (node sequences closing on the start)."""
        deps: dict[str, list[str]] = defaultdict(list)
        for skill_id, data in graph.items():
            for prereq in data.get("prerequisites") or []:
                deps[skill_id].append(str(prereq))

        visited: set[str] = set()
        stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            if node in stack:
                if node in path:
                    start = path.index(node)
                    cycles.append(path[start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in deps.get(node, []):
                dfs(neighbor, path)
            path.pop()
            stack.remove(node)

        for skill in list(deps.keys()):
            if skill not in visited:
                dfs(skill, [])
        return cycles

    @staticmethod
    def validate_graph(graph: dict[str, dict[str, Any]]) -> dict[str, Any]:
        report: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {
                "total_skills": len(graph),
                "skills_with_prerequisites": 0,
                "avg_prerequisites": 0.0,
            },
        }
        cycles = GraphValidator.detect_circular_dependency(graph)
        if cycles:
            report["valid"] = False
            report["errors"].append(
                {
                    "type": "circular_dependency",
                    "detail": f"发现 {len(cycles)} 个循环依赖",
                    "cycles": cycles,
                }
            )

        all_prereqs: set[str] = set()
        for data in graph.values():
            all_prereqs.update(str(p) for p in (data.get("prerequisites") or []))

        # Nodes that appear as prerequisites of others but are missing from graph
        missing = sorted(p for p in all_prereqs if p not in graph)
        if missing:
            report["valid"] = False
            report["errors"].append(
                {
                    "type": "missing_prerequisite_node",
                    "detail": f"缺失 {len(missing)} 个前置节点",
                    "skills": missing[:20],
                }
            )

        prereq_counts = [len(data.get("prerequisites") or []) for data in graph.values()]
        report["stats"]["skills_with_prerequisites"] = sum(
            1 for count in prereq_counts if count > 0
        )
        report["stats"]["avg_prerequisites"] = (
            sum(prereq_counts) / len(prereq_counts) if prereq_counts else 0.0
        )
        return report

    @staticmethod
    def from_cognitive_nodes(
        nodes: list[Any],
    ) -> dict[str, dict[str, Any]]:
        """Adapt SkillNode list to validator graph shape."""
        graph: dict[str, dict[str, Any]] = {}
        for node in nodes:
            skill_id = getattr(node, "skill_id", None) or node["skill_id"]
            prereqs = getattr(node, "prerequisites", None)
            if prereqs is None:
                prereqs = node.get("prerequisites") or []
            graph[str(skill_id)] = {"prerequisites": list(prereqs)}
        return graph
