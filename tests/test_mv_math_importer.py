"""Tests for MV-MATH curriculum binding importer."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.curriculum_gate import CurriculumGate
from ilearn.data.importers.mv_math import (
    iter_mv_math_records,
    load_bindings,
    resolve_binding,
    to_multimodal_item,
)

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "mv_math_tiny.json"
BINDINGS = REPO / "data" / "curriculum" / "mv_math_bindings.json"


def _bindings() -> dict:
    return load_bindings(BINDINGS)


def _example_bank_rect_area() -> dict[str, list[dict]]:
    return {
        "rect_area": [
            {
                "id": "ex-rect-1",
                "stem": "观察图中长方形，求面积是多少平方厘米？",
                "answer": "40",
                "chapter": "长方形面积",
                "label": "北京·人教·小学数学",
            },
            {
                "id": "ex-rect-2",
                "stem": "长方形长 6 厘米、宽 4 厘米，面积是多少？",
                "answer": "24",
                "chapter": "长方形面积",
                "label": "北京·人教·小学数学",
            },
        ]
    }


def test_iter_mv_math_records():
    rows = list(iter_mv_math_records(FIX))
    assert len(rows) == 3


def test_resolve_binding_maps_metric_geometry_rectangle_to_rect_area():
    bindings = _bindings()
    records = list(iter_mv_math_records(FIX))
    bind = resolve_binding(records[0], bindings["rules"], bindings)
    assert bind is not None
    assert bind["knowledge_ids"] == ["rect_area"]
    assert bind["chapter"] == "长方形面积"


def test_resolve_binding_skips_non_elementary_when_grade_map_empty():
    bindings = _bindings()
    records = list(iter_mv_math_records(FIX))
    bind = resolve_binding(records[2], bindings["rules"], bindings)
    assert bind is None


def test_to_multimodal_item_passes_curriculum_gate():
    bindings = _bindings()
    records = list(iter_mv_math_records(FIX))
    bind = resolve_binding(records[0], bindings["rules"], bindings)
    assert bind is not None

    image_paths = [
        "assets/mv_math/mmv-test_rect_001/0.png",
        "assets/mv_math/mmv-test_rect_001/1.png",
    ]
    item = to_multimodal_item(
        records[0],
        bind,
        image_paths,
        _example_bank_rect_area(),
    )
    assert item is not None
    gate = CurriculumGate()
    errors = gate.validate_item(item)
    assert errors == []
    assert item["curriculum_ref"]["chapter"] == "长方形面积"
    assert item["knowledge_ids"] == ["rect_area"]


def test_english_question_gets_chinese_stem_from_example_bank():
    bindings = _bindings()
    records = list(iter_mv_math_records(FIX))
    bind = resolve_binding(records[0], bindings["rules"], bindings)
    assert bind is not None

    bank = _example_bank_rect_area()
    item = to_multimodal_item(
        records[0],
        bind,
        ["assets/mv_math/mmv-test_rect_001/0.png"],
        bank,
    )
    assert item is not None
    assert "长方形" in item["stem"]
    assert not item["stem"].startswith("A rectangle")

    # Deterministic hash by problem_id
    item2 = to_multimodal_item(
        records[0],
        bind,
        ["assets/mv_math/mmv-test_rect_001/0.png"],
        bank,
    )
    assert item2 is not None
    assert item2["stem"] == item["stem"]


def test_choice_answer_type_uses_chinese_stem():
    bindings = _bindings()
    record = {
        "problem_id": "choice_rect",
        "question": "Which option shows the correct rectangle?",
        "answer": "C",
        "answer_type": "choice",
        "difficulty": "Low",
        "grade": "Elementary",
        "subject": "Metric Geometry",
        "image_relavance": "0",
    }
    bind = resolve_binding(record, bindings["rules"], bindings)
    assert bind is not None
    item = to_multimodal_item(
        record,
        bind,
        ["assets/mv_math/mmv-choice_rect/0.png"],
        _example_bank_rect_area(),
    )
    assert item is not None
    assert "长方形" in item["stem"]
    assert item["answer"] == "C"
