from ilearn.core.hints import hint_for_error


def test_hint_never_contains_numeric_answer_key_pattern():
    level, text = hint_for_error("calc_error", fail_streak=0)
    assert level == "low"
    assert "答案" not in text or "不要直接看答案" in hint_for_error("calc_error", 3)[1]


def test_fail_streak_escalates_to_high():
    level, _ = hint_for_error("misread", fail_streak=3)
    assert level == "high"


def test_hint_does_not_embed_answer_key():
    _, text = hint_for_error("concept_gap", 0)
    assert "answer_key" not in text.casefold()
