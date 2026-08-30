from pathlib import Path

import pytest

from ilearn.core.subject_adapter import MathSubjectAdapter, get_adapter
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
