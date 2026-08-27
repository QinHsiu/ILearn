"""Orchestrate pilot curriculum rebuild from raw importers."""

from __future__ import annotations

import argparse
import json
import logging
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

RCAE_URL = (
    "https://raw.githubusercontent.com/digitalboy/RCAE_graph_data/main/"
    "china_primary_school_math_knowledge_graph.json"
)
RCAE_DOWNLOAD_TIMEOUT = 120

from ilearn.core.curriculum_gate import CurriculumGate
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.data.importers.mm_k12 import iter_mm_k12_records, to_example_entry
from ilearn.data.importers.mv_math import (
    _item_id,
    extract_images,
    iter_mv_math_records,
    load_bindings,
    resolve_binding,
    to_multimodal_item,
)
from ilearn.data.importers.rcae_graph import parse_rcae, to_ilearn_graph, to_ilearn_knowledge
from ilearn.data.importers.tal_scq5k import stem_hash_prefix, to_example_from_scq5k
from ilearn.data.importers.template_examples import supplement_legacy_from_templates
from ilearn.data.kp_ids import extend_alias_from_knowledge, load_alias_map

REPO_ROOT = Path(__file__).resolve().parents[2]
RCAE_FILENAME = "china_primary_school_math_knowledge_graph.json"
PILOT_GRADES = (4, 5, 6)
DIFF_BUCKETS = ("easy", "medium", "hard")
MAX_PER_BUCKET = 4
MAX_PER_KP = 12

LEGACY_KNOWLEDGE: list[dict] = [
    {"id": "mult_3digit", "grade": 4, "name": "三位数乘两位数", "ability_tags": ["mental_math"]},
    {"id": "rect_area", "grade": 4, "name": "长方形面积", "ability_tags": ["spatial"]},
    {"id": "angle_measure", "grade": 4, "name": "角的度量", "ability_tags": ["spatial"]},
    {"id": "parallel_perp", "grade": 4, "name": "平行与垂直", "ability_tags": ["logic"]},
    {"id": "dec_mult", "grade": 5, "name": "小数乘法", "ability_tags": ["mental_math"]},
    {"id": "frac_add_same", "grade": 5, "name": "同分母分数加法", "ability_tags": ["logic"]},
    {"id": "frac_mult", "grade": 5, "name": "分数乘法", "ability_tags": ["logic"]},
    {"id": "simple_eq", "grade": 5, "name": "简易方程", "ability_tags": ["logic"]},
    {"id": "frac_div", "grade": 6, "name": "分数除法", "ability_tags": ["logic"]},
    {"id": "ratio", "grade": 6, "name": "比和比例", "ability_tags": ["logic"]},
    {"id": "circle_area", "grade": 6, "name": "圆的面积", "ability_tags": ["spatial"]},
    {"id": "percent", "grade": 6, "name": "百分数应用", "ability_tags": ["mental_math"]},
    {"id": "factors", "grade": 6, "name": "因数与倍数", "ability_tags": ["logic"]},
]

LEGACY_GRAPH: dict[str, dict] = {
    "mult_3digit": {"prerequisites": [], "related": ["rect_area"], "grade": 4},
    "rect_area": {"prerequisites": ["mult_3digit"], "related": ["parallel_perp"], "grade": 4},
    "angle_measure": {"prerequisites": [], "related": ["parallel_perp"], "grade": 4},
    "parallel_perp": {"prerequisites": ["angle_measure"], "related": ["rect_area"], "grade": 4},
    "dec_mult": {"prerequisites": ["mult_3digit"], "related": ["frac_mult"], "grade": 5},
    "frac_add_same": {"prerequisites": [], "related": ["frac_mult", "frac_div"], "grade": 5},
    "frac_mult": {"prerequisites": ["frac_add_same"], "related": ["frac_div", "dec_mult"], "grade": 5},
    "simple_eq": {"prerequisites": ["dec_mult"], "related": ["frac_mult"], "grade": 5},
    "frac_div": {"prerequisites": ["frac_mult"], "related": ["ratio"], "grade": 6},
    "ratio": {"prerequisites": ["frac_div"], "related": ["percent"], "grade": 6},
    "circle_area": {"prerequisites": ["rect_area"], "related": ["percent"], "grade": 6},
    "percent": {"prerequisites": ["ratio"], "related": ["frac_div"], "grade": 6},
    "factors": {"prerequisites": ["mult_3digit"], "related": ["frac_div"], "grade": 6},
}


@dataclass
class BuildReport:
    knowledge_count: int = 0
    example_count: int = 0
    graph_nodes: int = 0
    multimodal_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_existing_knowledge(out_pilot: Path) -> list[dict]:
    path = out_pilot / "knowledge.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data) if isinstance(data, list) else []


def _load_existing_example_bank(out_pilot: Path) -> dict[str, list[dict]]:
    path = out_pilot / "example_bank.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {kp_id: list(examples) for kp_id, examples in data.items() if isinstance(examples, list)}


def _download_rcae_if_missing(raw_dir: Path, warnings: list[str]) -> bool:
    """Attempt RCAE download when raw file absent. Returns True if file exists after call."""
    rcae_dir = raw_dir / "rcae"
    rcae_path = rcae_dir / RCAE_FILENAME
    if rcae_path.is_file():
        return True

    rcae_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        RCAE_URL,
        headers={"User-Agent": "ILearn-build-pilot/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=RCAE_DOWNLOAD_TIMEOUT) as response:
            payload = response.read()
        rcae_path.write_bytes(payload)
        logger.info("Downloaded RCAE graph to %s", rcae_path)
        return True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        msg = f"RCAE download failed ({exc}); continuing with existing pilot knowledge only"
        warnings.append(msg)
        logger.warning(msg)
        return False


def _union_knowledge(*sources: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for entries in sources:
        for entry in entries:
            kp_id = entry.get("id")
            if not kp_id:
                continue
            if kp_id in by_id:
                merged = dict(by_id[kp_id])
                merged.update(entry)
                if entry.get("ability_tags"):
                    merged["ability_tags"] = entry["ability_tags"]
                elif by_id[kp_id].get("ability_tags"):
                    merged["ability_tags"] = by_id[kp_id]["ability_tags"]
                by_id[kp_id] = merged
            else:
                by_id[kp_id] = dict(entry)
    return sorted(by_id.values(), key=lambda item: (item.get("grade", 0), item.get("id", "")))


def _load_existing_graph(out_graph: Path) -> dict[str, dict]:
    if not out_graph.is_file():
        return {}
    data = json.loads(out_graph.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, dict) else {}


def _merge_graph_nodes(*sources: dict[str, dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for graph in sources:
        for kp_id, node in graph.items():
            if kp_id not in merged:
                merged[kp_id] = {
                    "prerequisites": list(node.get("prerequisites", [])),
                    "related": list(node.get("related", [])),
                    "grade": node.get("grade", 0),
                }
                continue
            target = merged[kp_id]
            for key in ("prerequisites", "related"):
                for value in node.get(key, []):
                    if value not in target[key]:
                        target[key].append(value)
            if not target.get("grade") and node.get("grade"):
                target["grade"] = node["grade"]
    return merged


def _ensure_graph_nodes(graph: dict[str, dict], knowledge: list[dict]) -> dict[str, dict]:
    result = dict(graph)
    for entry in knowledge:
        kp_id = entry["id"]
        if kp_id not in result:
            result[kp_id] = {"prerequisites": [], "related": [], "grade": entry["grade"]}
        elif "grade" not in result[kp_id]:
            result[kp_id]["grade"] = entry["grade"]
    return result


def _bucket_counts(examples: list[dict]) -> dict[str, int]:
    counts = {bucket: 0 for bucket in DIFF_BUCKETS}
    for example in examples:
        difficulty = example.get("difficulty", "medium")
        if difficulty in counts:
            counts[difficulty] += 1
    return counts


def _can_add_example(examples: list[dict], example: dict) -> bool:
    if len(examples) >= MAX_PER_KP:
        return False
    difficulty = example.get("difficulty", "medium")
    if difficulty not in DIFF_BUCKETS:
        difficulty = "medium"
    return _bucket_counts(examples)[difficulty] < MAX_PER_BUCKET


def _add_example(
    bank: dict[str, list[dict]],
    kp_id: str,
    example: dict,
    seen_stems: dict[str, set[str]],
) -> bool:
    stem_key = stem_hash_prefix(example.get("stem", ""))
    seen = seen_stems.setdefault(kp_id, set())
    if stem_key in seen:
        return False
    entries = bank.setdefault(kp_id, [])
    if not _can_add_example(entries, example):
        return False
    seen.add(stem_key)
    entries.append(example)
    return True


def _load_mm_k12_examples(raw_dir: Path, alias_map: dict[str, str]) -> dict[str, list[dict]]:
    bank: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set[str]] = {}
    mm_dir = raw_dir / "mm_k12"
    if not mm_dir.is_dir():
        return bank
    for path in sorted(mm_dir.glob("*.jsonl")):
        for record in iter_mm_k12_records(path):
            mapped = to_example_entry(record, alias_map)
            if mapped is None:
                continue
            kp_id, example = mapped
            _add_example(bank, kp_id, example, seen)
    return bank


def _load_tal_examples(raw_dir: Path, alias_map: dict[str, str]) -> dict[str, list[dict]]:
    bank: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set[str]] = {}
    tal_dir = raw_dir / "tal_scq5k"
    if not tal_dir.is_dir():
        return bank
    for path in sorted(tal_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                mapped = to_example_from_scq5k(record, alias_map, hard_only=False)
                if mapped is None:
                    continue
                kp_id, example = mapped
                _add_example(bank, kp_id, example, seen)
    return bank


def _merge_example_banks(*banks: dict[str, list[dict]]) -> dict[str, list[dict]]:
    merged: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set[str]] = {}
    for bank in banks:
        for kp_id, examples in bank.items():
            for example in examples:
                _add_example(merged, kp_id, example, seen)
    return dict(merged)


def _minimal_progress_mapping(knowledge: list[dict]) -> dict:
    mapping: dict = {"北京": {"人教版": {}}}
    for grade in PILOT_GRADES:
        grade_key = f"{grade}年级"
        grade_kps = [entry for entry in knowledge if entry.get("grade") == grade]
        chapters = []
        week_start = 1
        for entry in sorted(grade_kps, key=lambda item: item["id"]):
            chapters.append(
                {
                    "chapter": entry["name"],
                    "weeks": list(range(week_start, week_start + 4)),
                    "knowledge_ids": [entry["id"]],
                }
            )
            week_start += 4
        mapping["北京"]["人教版"][grade_key] = {
            "上学期": {"chapters": chapters},
            "下学期": {"chapters": []},
        }
    return mapping


def _load_chapter_overrides(repo_root: Path) -> dict | None:
    overrides_path = repo_root / "data" / "curriculum" / "chapter_overrides.json"
    if not overrides_path.is_file():
        return None
    return json.loads(overrides_path.read_text(encoding="utf-8"))


def _merge_progress_mapping(base: dict, overrides: dict) -> dict:
    """Deep-merge progress mapping; override grade entries replace base."""
    result = json.loads(json.dumps(base))
    for region, editions in overrides.items():
        result.setdefault(region, {})
        for edition, grades in editions.items():
            result[region].setdefault(edition, {})
            for grade, semesters in grades.items():
                result[region][edition][grade] = json.loads(json.dumps(semesters))
    return result


def _resolve_progress_mapping(
    knowledge: list[dict],
    repo_root: Path,
    warnings: list[str],
) -> dict:
    minimal = _minimal_progress_mapping(knowledge)
    overrides = _load_chapter_overrides(repo_root)
    if overrides is None:
        warnings.append(
            "chapter_overrides.json not found; wrote minimal Beijing/Renjiao progress mapping"
        )
        return minimal
    return _merge_progress_mapping(minimal, overrides)


def _find_mv_math_items_path(raw_dir: Path) -> Path | None:
    mv_dir = raw_dir / "mv_math"
    if not mv_dir.is_dir():
        return None
    preferred = mv_dir / "items.jsonl"
    if preferred.is_file():
        return preferred
    for path in sorted(mv_dir.glob("*.jsonl")):
        return path
    for path in sorted(mv_dir.glob("*.json")):
        return path
    return None


def build_multimodal_bank(
    raw_dir: Path,
    bindings_path: Path,
    pilot_dir: Path,
    example_bank_path: Path,
    overrides_path: Path,
    syllabus_path: Path,
    graph_path: Path,
    max_items: int = 80,
) -> tuple[list[dict], list[str]]:
    """Import curriculum-bound MV-MATH items into the multimodal bank."""
    warnings: list[str] = []
    items_path = _find_mv_math_items_path(raw_dir)
    if items_path is None:
        warnings.append("mv_math raw data not found; wrote empty multimodal_bank.json")
        return [], warnings

    bindings = load_bindings(bindings_path)
    rules = bindings.get("rules", [])
    example_bank = json.loads(example_bank_path.read_text(encoding="utf-8"))
    if not isinstance(example_bank, dict):
        example_bank = {}

    gate = CurriculumGate(
        overrides_path=overrides_path,
        syllabus_path=syllabus_path,
        graph=KnowledgeGraph(graph_path),
    )

    mv_dir = raw_dir / "mv_math"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []

    for record in iter_mv_math_records(items_path):
        if len(items) >= max_items:
            break

        bind = resolve_binding(record, rules, bindings)
        if bind is None:
            continue

        problem_id = str(record.get("problem_id") or "").strip()
        if not problem_id:
            continue

        item_id = _item_id(problem_id)
        image_paths = extract_images(record, mv_dir, pilot_dir, item_id)
        item = to_multimodal_item(
            record,
            bind,
            image_paths,
            example_bank,
            overrides_path=overrides_path,
        )
        if item is None:
            continue

        errors = gate.validate_item(item)
        if errors:
            warnings.append(
                f"skipped invalid multimodal item {item.get('id', problem_id)}: {errors[0]}"
            )
            continue

        items.append(item)

    if not items:
        warnings.append("no valid multimodal items imported from mv_math")

    return items, warnings


def _validate(
    knowledge: list[dict],
    graph: dict[str, dict],
    example_bank: dict[str, list[dict]],
    warnings: list[str],
) -> None:
    knowledge_ids = {entry["id"] for entry in knowledge}
    for kp_id in sorted(knowledge_ids):
        if kp_id not in graph:
            warnings.append(f"knowledge_id {kp_id} missing from knowledge_graph.json")
        examples = example_bank.get(kp_id, [])
        if not examples:
            warnings.append(f"knowledge_id {kp_id} has no examples")
        elif len(examples) < 8:
            warnings.append(f"knowledge_id {kp_id} has fewer than 8 examples ({len(examples)})")

    for kp_id, node in graph.items():
        for prereq in node.get("prerequisites", []):
            if prereq not in knowledge_ids:
                warnings.append(f"orphan prerequisite {prereq} on {kp_id}")


def build_pilot(
    raw_dir: Path,
    out_pilot: Path,
    out_graph: Path,
    out_progress: Path,
    alias_path: Path,
) -> BuildReport:
    warnings: list[str] = []
    alias_map = load_alias_map(alias_path)

    _download_rcae_if_missing(raw_dir, warnings)
    rcae_path = raw_dir / "rcae" / RCAE_FILENAME
    rcae_knowledge: list[dict] = []
    graph: dict[str, dict] = {}
    if rcae_path.is_file():
        nodes, edges = parse_rcae(rcae_path)
        rcae_knowledge = to_ilearn_knowledge(nodes, alias_map, grades=PILOT_GRADES)
        graph = to_ilearn_graph(nodes, edges, alias_map, grades=PILOT_GRADES)
    else:
        warnings.append(f"RCAE file missing: {rcae_path}; continuing with legacy knowledge only")

    existing_graph = _load_existing_graph(out_graph)
    existing_knowledge = _load_existing_knowledge(out_pilot)
    knowledge = _union_knowledge(LEGACY_KNOWLEDGE, existing_knowledge, rcae_knowledge)
    graph = _merge_graph_nodes(LEGACY_GRAPH, existing_graph, graph)
    graph = _ensure_graph_nodes(graph, knowledge)

    existing_bank = _load_existing_example_bank(out_pilot)
    alias_for_examples = extend_alias_from_knowledge(knowledge, alias_map)
    mm_bank = _load_mm_k12_examples(raw_dir, alias_for_examples)
    tal_bank = _load_tal_examples(raw_dir, alias_for_examples)
    example_bank = _merge_example_banks(existing_bank, mm_bank, tal_bank)
    templates_path = out_pilot / "templates.json"
    if not templates_path.is_file():
        templates_path = REPO_ROOT / "data" / "pilot" / "templates.json"
    example_bank = supplement_legacy_from_templates(
        example_bank,
        templates_path,
        LEGACY_KNOWLEDGE,
        min_per_kp=8,
    )

    progress = _resolve_progress_mapping(knowledge, REPO_ROOT, warnings)
    _validate(knowledge, graph, example_bank, warnings)

    out_pilot.mkdir(parents=True, exist_ok=True)
    _write_json(out_pilot / "example_bank.json", example_bank)

    bindings_path = REPO_ROOT / "data" / "curriculum" / "mv_math_bindings.json"
    overrides_path = REPO_ROOT / "data" / "curriculum" / "chapter_overrides.json"
    syllabus_path = out_pilot / "syllabus.json"
    if not syllabus_path.is_file():
        syllabus_path = REPO_ROOT / "data" / "pilot" / "syllabus.json"
    multimodal_items, multimodal_warnings = build_multimodal_bank(
        raw_dir=raw_dir,
        bindings_path=bindings_path,
        pilot_dir=out_pilot,
        example_bank_path=out_pilot / "example_bank.json",
        overrides_path=overrides_path,
        syllabus_path=syllabus_path,
        graph_path=out_graph,
        max_items=80,
    )
    warnings.extend(multimodal_warnings)

    _write_json(out_pilot / "knowledge.json", knowledge)
    _write_json(out_pilot / "multimodal_bank.json", multimodal_items)
    _write_json(out_graph, graph)
    _write_json(out_progress, progress)

    example_count = sum(len(items) for items in example_bank.values())
    return BuildReport(
        knowledge_count=len(knowledge),
        example_count=example_count,
        graph_nodes=len(graph),
        multimodal_count=len(multimodal_items),
        warnings=warnings,
    )


def _default_paths() -> argparse.Namespace:
    return argparse.Namespace(
        raw_dir=REPO_ROOT / "data" / "raw",
        pilot_dir=REPO_ROOT / "data" / "pilot",
        graph=REPO_ROOT / "data" / "knowledge_graph.json",
        progress=REPO_ROOT / "data" / "curriculum" / "progress_mapping.json",
        alias=REPO_ROOT / "data" / "curriculum" / "kp_alias.json",
    )


def _print_summary(report: BuildReport) -> None:
    print(f"knowledge_count={report.knowledge_count}")
    print(f"example_count={report.example_count}")
    print(f"graph_nodes={report.graph_nodes}")
    print(f"multimodal_count={report.multimodal_count}")
    if report.warnings:
        print("warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    defaults = _default_paths()
    parser = argparse.ArgumentParser(description="Rebuild ILearn pilot curriculum data")
    parser.add_argument("--raw-dir", type=Path, default=defaults.raw_dir)
    parser.add_argument("--pilot-dir", type=Path, default=defaults.pilot_dir)
    parser.add_argument("--graph", type=Path, default=defaults.graph)
    parser.add_argument("--progress", type=Path, default=defaults.progress)
    parser.add_argument("--alias", type=Path, default=defaults.alias)
    args = parser.parse_args(argv)

    report = build_pilot(
        raw_dir=args.raw_dir,
        out_pilot=args.pilot_dir,
        out_graph=args.graph,
        out_progress=args.progress,
        alias_path=args.alias,
    )
    _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
