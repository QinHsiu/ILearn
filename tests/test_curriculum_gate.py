"""Tests for CurriculumGate validation and profile filtering."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ilearn.core.curriculum_gate import CurriculumGate
from ilearn.core.schemas import StudentProfile

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
BEIJING = "北京"
FALL = "上学期"
SPRING = "下学期"


def _load_fixture() -> list[dict]:
    with (FIXTURES / "multimodal_tiny.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _gate() -> CurriculumGate:
    return CurriculumGate()


def test_validate_item_accepts_valid_fixture_rows():
    gate = _gate()
    items = _load_fixture()
    assert gate.validate_item(items[0]) == []
    assert gate.validate_item(items[1]) == []


def test_validate_item_rejects_invalid_chapter():
    gate = _gate()
    items = _load_fixture()
    errors = gate.validate_item(items[2])
    assert errors
    assert any("chapter not found" in err for err in errors)


def test_eligible_for_profile_when_profile_matches_progress():
    gate = _gate()
    items = _load_fixture()
    profile = StudentProfile(region=BEIJING, grade=4, age=10)
    now = datetime(2026, 1, 15)
    assert gate.eligible_for_profile(
        items[0],
        profile,
        semester=FALL,
        now=now,
        current_kps=["rect_area", "mult_3digit"],
    )


def test_eligible_for_profile_false_when_grade_mismatch():
    gate = _gate()
    items = _load_fixture()
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    now = datetime(2026, 1, 15)
    assert not gate.eligible_for_profile(
        items[0],
        profile,
        semester=FALL,
        now=now,
        current_kps=["rect_area", "mult_3digit"],
    )


def test_filter_bank_returns_only_eligible_items():
    gate = _gate()
    items = _load_fixture()
    profile = StudentProfile(region=BEIJING, grade=4, age=10)
    now = datetime(2026, 1, 15)
    eligible = gate.filter_bank(
        items,
        profile,
        semester=FALL,
        now=now,
        knowledge_ids=["rect_area", "mult_3digit"],
    )
    ids = {item["id"] for item in eligible}
    assert ids == {"mmv-rect-001"}


def test_filter_bank_grade5_semester_fall():
    gate = _gate()
    items = _load_fixture()
    profile = StudentProfile(region=BEIJING, grade=5, age=11)
    now = datetime(2026, 10, 1)
    eligible = gate.filter_bank(
        items,
        profile,
        semester=FALL,
        now=now,
        knowledge_ids=["dec_mult", "mult_3digit"],
    )
    ids = {item["id"] for item in eligible}
    assert ids == {"mmv-dec-001"}
