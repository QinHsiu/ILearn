"""Independent verify / replay of proactive dispatch receipts."""

from __future__ import annotations

from datetime import timezone

from ilearn.core.learner_state import LearnerState
from ilearn.scheduler.models import ProactiveDispatchReceipt


def verify_receipt(receipt: ProactiveDispatchReceipt) -> bool:
    """Recompute hash and compare — detects tampering."""
    return bool(receipt.receipt_hash) and receipt.receipt_hash == receipt.compute_hash()


def replay_receipt(receipt: ProactiveDispatchReceipt, state_at_version: LearnerState) -> bool:
    """Replay trigger conditions on the sealed LearnerState snapshot."""
    if state_at_version.version != receipt.state_version:
        raise ValueError("state version mismatch")
    if receipt.state_hash and state_at_version.state_hash != receipt.state_hash:
        raise ValueError("state hash mismatch — state was tampered")

    now = receipt.scheduled_at
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if receipt.trigger == "spaced_repetition":
        due = []
        for sid, dt in state_at_version.review_schedule.items():
            due_aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            if due_aware <= now:
                due.append(sid)
        return set(due) >= set(receipt.skill_ids)

    if receipt.trigger == "engagement_drop":
        signals = state_at_version.engagement_signals or {}
        days = int(signals.get("consecutive_inactive_days") or 0)
        loops = int(signals.get("loop_count") or 0)
        frustration = float(signals.get("frustration") or 0.0)
        return days >= 3 or (loops >= 2 and frustration >= 0.6)

    if receipt.trigger == "goal_deviation":
        deviation = float(
            (state_at_version.engagement_signals or {}).get("goal_deviation_ratio") or 0.0
        )
        return deviation > 0.3

    return True
