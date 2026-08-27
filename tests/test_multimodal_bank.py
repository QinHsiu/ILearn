"""Tests for build_pilot multimodal bank integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ilearn.core.curriculum_gate import CurriculumGate
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.data.build_pilot import build_multimodal_bank, build_pilot

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
ALIAS = REPO_ROOT / "data" / "curriculum" / "kp_alias.json"
BINDINGS = REPO_ROOT / "data" / "curriculum" / "mv_math_bindings.json"
OVERRIDES = REPO_ROOT / "data" / "curriculum" / "chapter_overrides.json"
SYLLABUS = REPO_ROOT / "data" / "pilot" / "syllabus.json"
MV_MATH_FIX = FIXTURES / "mv_math_tiny.json"


def _setup_mv_math_raw(raw: Path) -> None:
    mv_dir = raw / "mv_math"
    mv_dir.mkdir(parents=True)
    shutil.copy(MV_MATH_FIX, mv_dir / "items.json")
    for problem_id in ("test_rect_001", "test_angle_002"):
        img_dir = mv_dir / "images" / problem_id
        img_dir.mkdir(parents=True)
        (img_dir / "0.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01")


def _write_minimal_example_bank(pilot: Path) -> None:
    pilot.mkdir(parents=True, exist_ok=True)
    bank = {
        "rect_area": [
            {
                "id": "ex-rect-1",
                "stem": "观察图中长方形，求面积是多少平方厘米？",
                "answer": "40",
                "chapter": "长方形面积",
                "label": "北京·人教·小学数学",
            }
        ],
        "angle_measure": [
            {
                "id": "ex-angle-1",
                "stem": "用量角器测量图中角的度数。",
                "answer": "60",
                "chapter": "角的度量",
                "label": "北京·人教·小学数学",
            }
        ],
    }
    (pilot / "example_bank.json").write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_build_multimodal_bank_writes_valid_items(tmp_path: Path):
    raw = tmp_path / "raw"
    pilot = tmp_path / "pilot"
    graph = tmp_path / "knowledge_graph.json"
    graph.write_text(json.dumps({"rect_area": {"prerequisites": [], "related": [], "grade": 4}}))

    _setup_mv_math_raw(raw)
    _write_minimal_example_bank(pilot)

    items, warnings = build_multimodal_bank(
        raw_dir=raw,
        bindings_path=BINDINGS,
        pilot_dir=pilot,
        example_bank_path=pilot / "example_bank.json",
        overrides_path=OVERRIDES,
        syllabus_path=SYLLABUS,
        graph_path=graph,
        max_items=80,
    )

    assert len(items) >= 2
    assert not any("not found" in warning for warning in warnings)

    gate = CurriculumGate(
        overrides_path=OVERRIDES,
        syllabus_path=SYLLABUS,
        graph=KnowledgeGraph(graph),
    )
    for item in items:
        assert gate.validate_item(item) == []
        assert item["image_paths"]
        for rel_path in item["image_paths"]:
            assert (pilot / rel_path).is_file()

    bank_path = pilot / "multimodal_bank.json"
    bank_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    loaded = json.loads(bank_path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert loaded[0]["curriculum_ref"]["region"] == "北京"


def test_build_multimodal_bank_empty_when_raw_missing(tmp_path: Path):
    pilot = tmp_path / "pilot"
    graph = tmp_path / "knowledge_graph.json"
    graph.write_text("{}")
    _write_minimal_example_bank(pilot)

    items, warnings = build_multimodal_bank(
        raw_dir=tmp_path / "raw",
        bindings_path=BINDINGS,
        pilot_dir=pilot,
        example_bank_path=pilot / "example_bank.json",
        overrides_path=OVERRIDES,
        syllabus_path=SYLLABUS,
        graph_path=graph,
    )

    assert items == []
    assert any("not found" in warning for warning in warnings)


def test_build_pilot_writes_multimodal_bank(tmp_path: Path):
    raw = tmp_path / "raw"
    rcae_dir = raw / "rcae"
    rcae_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES / "rcae_tiny.json",
        rcae_dir / "china_primary_school_math_knowledge_graph.json",
    )
    _setup_mv_math_raw(raw)

    pilot = tmp_path / "pilot"
    graph = tmp_path / "knowledge_graph.json"
    progress = tmp_path / "progress_mapping.json"

    report = build_pilot(raw, pilot, graph, progress, ALIAS)

    bank_path = pilot / "multimodal_bank.json"
    assert bank_path.is_file()
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    assert isinstance(bank, list)
    assert report.multimodal_count == len(bank)
    assert report.multimodal_count >= 1

    gate = CurriculumGate(
        overrides_path=OVERRIDES,
        syllabus_path=SYLLABUS,
        graph=KnowledgeGraph(graph),
    )
    for item in bank:
        assert gate.validate_item(item) == []
