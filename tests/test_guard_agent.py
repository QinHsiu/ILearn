import json
from pathlib import Path

from ilearn.agents.guard import GuardAgent, leak_miss_rate

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "leak_cases.json"


def test_guard_flags_explicit_answer():
    verdict = GuardAgent().check("这道题答案是20。", "20")
    assert verdict.is_leak is True
    assert verdict.confidence >= 0.8


def test_guard_flags_phrase_answer_shi():
    verdict = GuardAgent().check("答案是15，你算对了吗？", "15")
    assert verdict.is_leak is True
    assert verdict.confidence >= 0.7


def test_guard_flags_0815_strong_answer_phrases():
    for message in ("答案就是15", "结果等于15", "应该是15"):
        verdict = GuardAgent().check(message, "15")
        assert verdict.is_leak is True
        assert verdict.confidence >= 0.7


def test_guard_does_not_match_formula_prefix():
    verdict = GuardAgent().check("代入后得到 x=20。", "x=2")
    assert verdict.is_leak is False


def test_guard_allows_retry_hint_without_answer():
    verdict = GuardAgent().check(
        "让我们再算一遍，注意加法步骤，你觉得结果会是多少？", "12"
    )
    assert verdict.is_leak is False


def test_guard_exact_number_only_has_low_confidence():
    verdict = GuardAgent().check("我算到了15。", "15")
    assert verdict.is_leak is True
    assert verdict.confidence == 0.6


def test_guard_allows_socratic_hint():
    verdict = GuardAgent().check("先把已知条件写下来，再选择运算。", "20")
    assert verdict.is_leak is False


def test_leak_miss_rate_below_five_percent():
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert len(cases) >= 50
    check = GuardAgent().check
    missed = [
        row
        for row in cases
        if row["expect_leak"]
        and not check(row["message"], row["answer_key"]).is_leak
    ]
    assert missed == []
    rate = leak_miss_rate(cases, check)
    assert rate < 0.05
