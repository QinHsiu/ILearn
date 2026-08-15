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
