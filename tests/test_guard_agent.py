import json
from pathlib import Path

from ilearn.agents.guard import GuardAgent, leak_miss_rate

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "leak_cases.json"


def test_guard_flags_explicit_answer():
    verdict = GuardAgent().check("这道题答案是20。", "20")
    assert verdict.is_leak is True
    assert verdict.confidence >= 0.8


def test_guard_allows_socratic_hint():
    verdict = GuardAgent().check("先把已知条件写下来，再选择运算。", "20")
    assert verdict.is_leak is False


def test_leak_miss_rate_below_five_percent():
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert len(cases) >= 50
    rate = leak_miss_rate(cases, GuardAgent().check)
    assert rate < 0.05
