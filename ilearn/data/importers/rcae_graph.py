from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ilearn.data.kp_ids import stable_kp_id

logger = logging.getLogger(__name__)

_SCHEMA_LOGGED = False

_PREREQ_TYPES = frozenset({"prerequisite"})
_RELATED_TYPES = frozenset({"relatedto", "complementaryto"})
_INCLUDES_TYPES = frozenset({"includes"})
_CN_GRADE = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
_GRADE_TEXT = re.compile(r"小学([一二三四五六])年级")


def _normalize_edge_type(edge_type: str) -> str:
    return edge_type.strip().lower().replace(" ", "").replace("_", "")


def _node_label(node: dict) -> str:
    props = node.get("properties") or {}
    return (
        node.get("label")
        or node.get("name")
        or props.get("node_name")
        or props.get("name")
        or ""
    ).strip()


def _parse_grade_value(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    match = _GRADE_TEXT.search(text)
    if match:
        return _CN_GRADE.get(match.group(1))
    return None


def _node_grade(node: dict) -> int | None:
    props = node.get("properties") or {}
    for key in ("grade", "年级"):
        for source in (node, props):
            if key in source:
                grade = _parse_grade_value(source[key])
                if grade is not None:
                    return grade
    return None


def _node_id(node: dict) -> str | None:
    if node.get("id"):
        return str(node["id"])
    props = node.get("properties") or {}
    if props.get("uuid"):
        return str(props["uuid"])
    return None


def _normalize_rcae_nodes(raw_nodes: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for node in raw_nodes:
        node_id = _node_id(node)
        if not node_id:
            continue
        labels = node.get("labels") or []
        if labels and "KnowledgePoint" not in labels:
            continue
        label = _node_label(node)
        grade = _node_grade(node)
        normalized.append({"id": node_id, "label": label, "grade": grade})
    return normalized


def _normalize_rcae_edges(raw_edges: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for edge in raw_edges:
        source = edge.get("source") or edge.get("start_uuid")
        target = edge.get("target") or edge.get("end_uuid")
        edge_type = edge.get("type")
        if not source or not target or not edge_type:
            continue
        normalized.append({"source": source, "target": target, "type": edge_type})
    return normalized


def _infer_grades_from_includes(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    by_id = {node["id"]: node for node in nodes if "id" in node}
    grades: dict[str, int] = {}
    for node in nodes:
        node_id = node.get("id")
        if node_id is None:
            continue
        grade = _node_grade(node)
        if grade is not None:
            grades[node_id] = grade

    changed = True
    while changed:
        changed = False
        for edge in edges:
            edge_type = _normalize_edge_type(str(edge.get("type", "")))
            if edge_type not in _INCLUDES_TYPES:
                continue
            source_id = edge.get("source")
            target_id = edge.get("target")
            if not source_id or not target_id:
                continue
            parent_grade = grades.get(source_id)
            if parent_grade is None or target_id in grades:
                continue
            grades[target_id] = parent_grade
            changed = True
    return grades


def _log_schema_once(nodes: list[dict], edges: list[dict]) -> None:
    global _SCHEMA_LOGGED
    if _SCHEMA_LOGGED:
        return
    _SCHEMA_LOGGED = True
    node_sample = sorted(nodes[0].keys()) if nodes else []
    edge_sample = sorted(edges[0].keys()) if edges else []
    logger.info(
        "RCAE schema sample — node keys: %s; edge keys: %s; counts: %d nodes, %d edges",
        node_sample,
        edge_sample,
        len(nodes),
        len(edges),
    )


def parse_rcae(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        nodes: list[dict] = []
        edges: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            node = {k: v for k, v in item.items() if k != "edges"}
            nodes.append(node)
            edges.extend(item.get("edges", []))
    elif isinstance(data, dict) and "nodes" in data:
        nodes = list(data.get("nodes", []))
        edges = list(data.get("edges", []))
    else:
        raise ValueError(f"Unrecognized RCAE JSON shape in {path}")

    nodes = _normalize_rcae_nodes(nodes)
    edges = _normalize_rcae_edges(edges)
    _log_schema_once(nodes, edges)
    return nodes, edges


def _build_node_index(
    nodes: list[dict],
    edges: list[dict],
    alias_map: dict[str, str],
    grades: tuple[int, ...],
) -> tuple[dict[str, str], dict[str, int], dict[str, str]]:
    inferred_grades = _infer_grades_from_includes(nodes, edges)
    rcae_to_kp: dict[str, str] = {}
    kp_grades: dict[str, int] = {}
    kp_names: dict[str, str] = {}

    for node in nodes:
        rcae_id = node.get("id")
        if not rcae_id:
            continue
        label = _node_label(node)
        if not label:
            continue
        kp_id = stable_kp_id(label, alias_map)
        if kp_id is None:
            continue
        grade = _node_grade(node)
        if grade is None:
            grade = inferred_grades.get(rcae_id)
        if grade is None or grade not in grades:
            continue
        rcae_to_kp[rcae_id] = kp_id
        kp_grades[kp_id] = grade
        kp_names[kp_id] = label

    return rcae_to_kp, kp_grades, kp_names


def to_ilearn_knowledge(
    nodes: list[dict],
    alias_map: dict[str, str],
    grades: tuple[int, ...] = (4, 5, 6),
) -> list[dict]:
    _, kp_grades, kp_names = _build_node_index(nodes, [], alias_map, grades)
    return [
        {
            "id": kp_id,
            "grade": kp_grades[kp_id],
            "name": kp_names[kp_id],
            "ability_tags": [],
        }
        for kp_id in sorted(kp_names)
    ]


def to_ilearn_graph(
    nodes: list[dict],
    edges: list[dict],
    alias_map: dict[str, str],
    grades: tuple[int, ...] = (4, 5, 6),
) -> dict[str, dict]:
    rcae_to_kp, kp_grades, _ = _build_node_index(nodes, edges, alias_map, grades)
    graph: dict[str, dict] = {
        kp_id: {"prerequisites": [], "related": [], "grade": grade}
        for kp_id, grade in kp_grades.items()
    }

    def _append_unique(bucket: list[str], value: str) -> None:
        if value not in bucket:
            bucket.append(value)

    for edge in edges:
        source_kp = rcae_to_kp.get(edge.get("source", ""))
        target_kp = rcae_to_kp.get(edge.get("target", ""))
        if not source_kp or not target_kp or source_kp == target_kp:
            continue

        edge_type = _normalize_edge_type(str(edge.get("type", "")))
        if edge_type in _PREREQ_TYPES:
            _append_unique(graph[target_kp]["prerequisites"], source_kp)
        elif edge_type in _RELATED_TYPES:
            _append_unique(graph[source_kp]["related"], target_kp)
            _append_unique(graph[target_kp]["related"], source_kp)
        elif edge_type in _INCLUDES_TYPES:
            _append_unique(graph[target_kp]["related"], source_kp)

    return graph
