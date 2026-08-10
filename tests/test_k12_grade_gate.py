from pathlib import Path

import pytest

from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_profile_accepts_grade_8():
    StudentProfile(region="北京", grade=8, age=14)


def test_profile_accepts_grade_1():
    StudentProfile(region="北京", grade=1, age=7)


def test_pilot_provider_rejects_grade_8():
    with pytest.raises(Exception, match="试点"):
        PilotBeijingRenjiaoProvider(PILOT).list_knowledge(8)


def test_pilot_provider_rejects_grade_1():
    with pytest.raises(Exception, match="试点"):
        PilotBeijingRenjiaoProvider(PILOT).list_templates(1)


def test_pilot_provider_accepts_grade_5():
    nodes = PilotBeijingRenjiaoProvider(PILOT).list_knowledge(5)
    assert nodes
