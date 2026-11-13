"""SM-2 pure-function tests (P1)."""

from ilearn.scheduler.spaced_repetition import SM2State, sm2_update


def test_sm2_quality_5_second_review():
    # SM-2: review_count==1 → fixed interval 6; growth starts at review_count>=2
    second = sm2_update(SM2State(review_count=1, ease_factor=2.5, interval_days=1.0), quality=5)
    assert second.review_count == 2
    assert second.interval_days == 6.0
    third = sm2_update(second, quality=5)
    assert third.review_count == 3
    assert third.interval_days > 6.0


def test_sm2_quality_below_3_resets():
    state = SM2State(review_count=5, ease_factor=2.5, interval_days=30.0)
    nxt = sm2_update(state, quality=2)
    assert nxt.review_count == 0
    assert nxt.interval_days == 1.0


def test_sm2_deterministic():
    state = SM2State(review_count=2, ease_factor=2.4, interval_days=15.0)
    assert sm2_update(state, 4) == sm2_update(state, 4)
