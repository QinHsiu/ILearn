from ilearn.agents.math_verify_adapter import MathVerifyAdapter


def test_fraction_equivalence_two_four_vs_one_half():
    result = MathVerifyAdapter.is_equivalent("2/4", "1/2")
    assert result["equivalent"] is True
    assert result["confidence"] > 0.9


def test_unicode_fraction_equivalence():
    result = MathVerifyAdapter.is_equivalent("½", "1/2")
    assert result["equivalent"] is True
    assert result["confidence"] > 0.9


def test_non_equivalent_strings():
    result = MathVerifyAdapter.is_equivalent("苹果", "1/2")
    assert result["equivalent"] is False


def test_normalize_expression_preserves_mixed_number_spacing():
    assert MathVerifyAdapter.normalize_expression("1 1/2") == "1 1/2"


def test_mixed_number_is_equivalent_to_improper_fraction():
    result = MathVerifyAdapter.is_equivalent("1 1/2", "3/2")
    assert result["equivalent"] is True


def test_answers_match_accepts_mixed_number():
    from ilearn.core.grading import answers_match

    assert answers_match("1 1/2", "3/2")
