from pathlib import Path

import pytest

from ilearn.core.assessment import build_blueprint, build_blueprint_for_subject
from ilearn.core.schemas import StudentProfile
from ilearn.core.subject_quotas import load_quota

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_load_quota_chinese():
    quota = load_quota("chinese", PILOT)
    assert quota["subject"] == "chinese"
    assert sum(quota["layers"].values()) == 20
    assert sum(quota["types"].values()) == 20


def test_load_quota_math_returns_builtin():
    quota = load_quota("math", PILOT)
    assert quota["subject"] == "math"
    assert len(quota["slots"]) == 20


def test_build_blueprint_math_unchanged():
    profile = StudentProfile(region="北京", grade=5, age=11, subject="math")
    bp = build_blueprint(profile)
    assert len(bp.slots) == 20
    assert sum(1 for s in bp.slots if s.difficulty == "easy") == 10
    assert sum(1 for s in bp.slots if s.difficulty == "medium") == 8
    assert sum(1 for s in bp.slots if s.difficulty == "hard") == 2


def test_build_blueprint_for_subject_chinese_returns_20_slots():
    profile = StudentProfile(region="北京", grade=5, age=11, subject="chinese")
    bp = build_blueprint_for_subject(profile, PILOT)
    assert len(bp.slots) == 20
    assert sum(1 for s in bp.slots if s.difficulty == "easy") == 10
    assert sum(1 for s in bp.slots if s.difficulty == "medium") == 8
    assert sum(1 for s in bp.slots if s.difficulty == "hard") == 2
    assert sum(1 for s in bp.slots if s.item_type == "choice") == 8
    assert sum(1 for s in bp.slots if s.item_type == "fill") == 8
    assert sum(1 for s in bp.slots if s.item_type == "constructed") == 4


def test_build_blueprint_delegates_to_subject_template():
    profile = StudentProfile(region="北京", grade=5, age=11, subject="chinese")
    bp = build_blueprint(profile)
    assert len(bp.slots) == 20


def test_load_quota_unknown_subject_raises():
    with pytest.raises(ValueError, match="unknown subject"):
        load_quota("physics", PILOT)
