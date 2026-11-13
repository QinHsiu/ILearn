"""Proactive scheduler — SM-2 + dispatch receipts + consumption loop (no LLM)."""

from ilearn.scheduler.consumption import DispatchConsumption
from ilearn.scheduler.dispatcher import (
    Scheduler,
    build_review_events_from_mastery,
    due_dispatches,
)
from ilearn.scheduler.feedback import StateInvariantError, apply_consumption
from ilearn.scheduler.matcher import CONSUMPTION_WINDOW, ConsumptionMatcher
from ilearn.scheduler.models import ProactiveDispatchReceipt, ReviewItem
from ilearn.scheduler.replay import replay_receipt, verify_receipt
from ilearn.scheduler.spaced_repetition import SM2State, next_due, sm2_update
from ilearn.scheduler.trigger_policy import BetaArm, TriggerPolicy

__all__ = [
    "SM2State",
    "sm2_update",
    "next_due",
    "ProactiveDispatchReceipt",
    "ReviewItem",
    "Scheduler",
    "build_review_events_from_mastery",
    "due_dispatches",
    "verify_receipt",
    "replay_receipt",
    "DispatchConsumption",
    "ConsumptionMatcher",
    "CONSUMPTION_WINDOW",
    "apply_consumption",
    "StateInvariantError",
    "TriggerPolicy",
    "BetaArm",
]
