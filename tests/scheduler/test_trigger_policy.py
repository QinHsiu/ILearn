"""P4-deep: Beta-Bandit TriggerPolicy."""

from ilearn.scheduler.trigger_policy import TriggerPolicy


def test_thompson_ranking_is_deterministic_with_seed():
    policy = TriggerPolicy(rng_seed=42)
    a = policy.rank(["spaced_repetition", "engagement_drop", "goal_deviation"])
    b = TriggerPolicy.from_snapshot(policy.snapshot()).rank(
        ["spaced_repetition", "engagement_drop", "goal_deviation"]
    )
    assert a == b


def test_policy_prefers_successful_trigger_after_updates():
    policy = TriggerPolicy(rng_seed=7)
    for _ in range(50):
        policy.update("spaced_repetition", success=True)
        policy.update("engagement_drop", success=False)
    assert policy.arms["spaced_repetition"].mean > policy.arms["engagement_drop"].mean


def test_policy_snapshot_roundtrip():
    p = TriggerPolicy()
    p.update("goal_deviation", True)
    restored = TriggerPolicy.from_snapshot(p.snapshot())
    assert restored.arms["goal_deviation"].alpha == 2.0
