from pathlib import Path

import pytest

from ilearn.core.subject_adapter import MathSubjectAdapter, get_adapter, normalize_region
from ilearn.core.user_errors import ERROR_REGISTRY, map_exception_message
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_math_adapter_grade_range_and_supports():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    adapter = get_adapter("math", curriculum)
    assert isinstance(adapter, MathSubjectAdapter)
    assert adapter.get_grade_range() == (4, 6)
    assert adapter.supports(5) is True
    assert adapter.supports(3) is False
    assert adapter.curriculum() is curriculum
    nodes = adapter.curriculum().list_knowledge(5)
    assert len(nodes) >= 1


def test_unknown_subject_raises():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    with pytest.raises(ValueError, match="chinese"):
        get_adapter("chinese", curriculum)


def test_normalize_region_aliases():
    assert normalize_region("beijing") == "北京"
    assert normalize_region("上海") == "上海"
    assert normalize_region("shanghai") == "上海"
    assert normalize_region("广州") is None


def test_get_supported_regions_and_curriculum():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    adapter = get_adapter("math", curriculum)
    assert adapter.get_supported_regions() == ["北京", "上海"]
    bad_grade = adapter.get_curriculum(3, "北京")
    assert bad_grade["status"] == "unsupported"
    bad_region = adapter.get_curriculum(5, "广州")
    assert bad_region["status"] == "unsupported"
    ok = adapter.get_curriculum(5, "beijing")
    assert ok["status"] == "ok"
    assert ok["region"] == "北京"
    assert ok["grade"] == 5
    assert "label" in ok


def test_e004_registry_and_map():
    assert "E-004" in ERROR_REGISTRY
    mapped = map_exception_message("RegionNotSupported: 广州")
    assert mapped is not None
    assert mapped.code == "E-004"
