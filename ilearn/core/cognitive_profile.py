"""Cognitive skill graph (Bloom dimensions on top of knowledge points)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CognitiveDimension(Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


@dataclass
class SkillNode:
    """Skill node finer than a knowledge point, tagged with Bloom dimension."""

    skill_id: str
    name: str
    knowledge_point: str
    dimension: CognitiveDimension
    prerequisites: list[str] = field(default_factory=list)
    grade: int = 4
    examples: list[str] = field(default_factory=list)
    legacy_knowledge_ids: list[str] = field(default_factory=list)


class CognitiveSkillGraph:
    """Load and query the cognitive skill layer."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            root = Path(__file__).resolve().parents[2]
            path = root / "data" / "cognitive_skills.json"
        self.path = Path(path)
        self._nodes: dict[str, SkillNode] = {}
        self._load()

    def _load(self) -> None:
        from ilearn.core.cache import load_json_cached
        from ilearn.core.graph_validator import GraphValidator

        raw: Any = load_json_cached(self.path)
        skills = raw["skills"] if isinstance(raw, dict) and "skills" in raw else raw
        for item in skills:
            dim = CognitiveDimension(item["dimension"])
            node = SkillNode(
                skill_id=item["skill_id"],
                name=item["name"],
                knowledge_point=item["knowledge_point"],
                dimension=dim,
                prerequisites=list(item.get("prerequisites") or []),
                grade=int(item.get("grade", 4)),
                examples=list(item.get("examples") or []),
                legacy_knowledge_ids=list(item.get("legacy_knowledge_ids") or []),
            )
            self._nodes[node.skill_id] = node
        report = GraphValidator.validate_graph(
            GraphValidator.from_cognitive_nodes(self.all_skills())
        )
        for err in report.get("errors") or []:
            if err.get("type") == "circular_dependency":
                raise ValueError(
                    "cognitive skill graph has circular dependencies: "
                    f"{err.get('cycles') or []}"
                )

    def get(self, skill_id: str) -> SkillNode | None:
        return self._nodes.get(skill_id)

    def by_knowledge_point(self, kp: str) -> list[SkillNode]:
        return [n for n in self._nodes.values() if n.knowledge_point == kp]

    def by_legacy_knowledge_id(self, knowledge_id: str) -> list[SkillNode]:
        return [
            n
            for n in self._nodes.values()
            if knowledge_id in n.legacy_knowledge_ids or n.knowledge_point == knowledge_id
        ]

    def get_prerequisites(self, skill_id: str) -> list[str]:
        node = self._nodes.get(skill_id)
        return list(node.prerequisites) if node else []

    def all_skills(self) -> list[SkillNode]:
        return list(self._nodes.values())


def validate_cognitive_skills(path: Path) -> list[str]:
    """Return validation error strings; empty list means OK."""
    from ilearn.core.graph_validator import GraphValidator

    try:
        g = CognitiveSkillGraph(path)
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    ids = {n.skill_id for n in g.all_skills()}
    if not ids:
        errors.append("no skills found")
        return errors
    for n in g.all_skills():
        for prereq in n.prerequisites:
            if prereq not in ids:
                errors.append(f"{n.skill_id}: unknown prerequisite {prereq}")
        try:
            CognitiveDimension(n.dimension.value)
        except ValueError:
            errors.append(f"{n.skill_id}: invalid dimension")
    report = GraphValidator.validate_graph(
        GraphValidator.from_cognitive_nodes(g.all_skills())
    )
    for err in report.get("errors") or []:
        if err.get("type") == "circular_dependency":
            errors.append(f"circular_dependency: {err.get('detail')}")
        elif err.get("type") == "missing_prerequisite_node":
            # already covered by unknown prerequisite above
            continue
    return errors
