"""Tests for multimodal slots in adaptive assessment."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "data" / "pilot"
FIXTURES = Path(__file__).parent / "fixtures"
BEIJING = "北京"
FALL = "上学期"
SPRING = "下学期"


def _write_assets(pilot: Path, items: list[dict]) -> None:
    for row in items:
        for rel in row.get("image_paths") or []:
            path = pilot / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01")


def _make_pilot_dir(tmp_path: Path, multimodal_items: list[dict]) -> Path:
    pilot = tmp_path / "pilot"
    pilot.mkdir(parents=True)
    for name in ("knowledge.json", "templates.json", "syllabus.json", "example_bank.json"):
        src = PILOT / name
        if src.is_file():
            shutil.copy(src, pilot / name)
    (pilot / "multimodal_bank.json").write_text(
        json.dumps(multimodal_items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_assets(pilot, multimodal_items)
    return pilot


def _anchor_eligible_bank() -> list[dict]:
    base = json.loads((FIXTURES / "multimodal_tiny.json").read_text(encoding="utf-8"))
    valid = [row for row in base if row["id"] != "mmv-bad-chapter"]
    extra = {
        "id": "mmv-mult3-001",
        "stem": "计算 125 × 8 的结果。",
        "answer": "1000",
        "answer_type": "free-form",
        "difficulty": "easy",
        "knowledge_ids": ["mult_3digit"],
        "image_paths": ["assets/mv_math/mmv-mult3-001/0.png"],
        "curriculum_ref": {
            "region": "北京",
            "edition": "人教版",
            "grade": 4,
            "semester": FALL,
            "chapter": "三位数乘两位数",
            "weeks": [1, 2, 3, 4],
            "objective_ids": ["bj-g5-num-01"],
            "source_label": "北京·人教·小学数学",
        },
        "source": "mv_math",
    }
    return valid + [extra]


def test_anchor_injects_multimodal_when_bank_eligible(tmp_path: Path):
    pilot = _make_pilot_dir(tmp_path, _anchor_eligible_bank())
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(pilot))
    profile = StudentProfile(region=BEIJING, grade=4, age=10)
    result = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=FALL,
        now=datetime(2026, 1, 10),
    )
    assert result["is_anchor"] is True
    assert 2 <= result["multimodal_count"] <= 4
    assert result["delivered"] == result["requested"]
    mm_items = [item for item in result["paper"].items if item.is_multimodal]
    assert len(mm_items) == result["multimodal_count"]
    for item in mm_items:
        assert item.image_paths
        assert all(path.startswith("/pilot-assets/mv_math/") for path in item.image_paths)
        assert item.source_refs
        assert item.source_refs[0].textbook_chapter
    summary = result["curriculum_ref_summary"]
    assert summary["region"] == BEIJING
    assert summary["edition"] == "人教版"
    assert summary["grade"] == 4


def test_anchor_skips_multimodal_when_bank_empty(tmp_path: Path):
    pilot = _make_pilot_dir(tmp_path, [])
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(pilot))
    profile = StudentProfile(region=BEIJING, grade=4, age=10)
    result = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=FALL,
        now=datetime(2026, 1, 10),
    )
    assert result["multimodal_count"] == 0
    assert all(not item.is_multimodal for item in result["paper"].items)


def test_full_paper_stays_at_20_with_multimodal_cap(tmp_path: Path):
    pilot = _make_pilot_dir(tmp_path, _anchor_eligible_bank())
    agent = AssessmentAgent(PilotBeijingRenjiaoProvider(pilot))
    profile = StudentProfile(region=BEIJING, grade=4, age=10)
    anchor = agent.generate_adaptive_assessment(
        profile,
        is_first_time=True,
        semester=FALL,
        now=datetime(2026, 1, 10),
    )
    anchor_results = [
        {
            "item_id": item.id,
            "knowledge_ids": list(item.knowledge_ids),
            "is_correct": False,
        }
        for item in anchor["paper"].items
    ]
    full = agent.generate_adaptive_assessment(
        profile,
        is_first_time=False,
        anchor_results=anchor_results,
        semester=FALL,
        now=datetime(2026, 1, 10),
    )
    assert full["is_anchor"] is False
    assert len(full["paper"].items) == 20
    assert full["multimodal_count"] <= 4
    assert full["delivered"] == 20
