"""Fairness gap calculator — pure statistics over events + LearnerState (no LLM)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime

from ilearn.core.learner_state import LearnerState
from ilearn.fairness.metrics import FairnessAuditReport, GroupComparison


@dataclass
class FairnessConfig:
    min_group_size: int = 10
    mastery_gap_threshold: float = 0.10
    expired_rate_gap_threshold: float = 0.15
    hint_level_gap_threshold: float = 0.5


def compute_fairness(
    events: list[dict],
    learners: dict[str, LearnerState],
    attributes: dict[str, dict],
    attribute_name: str,
    cfg: FairnessConfig | None = None,
    window: tuple[datetime, datetime] | None = None,
) -> FairnessAuditReport:
    cfg = cfg or FairnessConfig()
    window = window or (datetime.min, datetime.max)
    mastery: dict[str, list[float]] = defaultdict(list)
    hints: dict[str, list[float]] = defaultdict(list)
    expired_rates: dict[str, list[float]] = defaultdict(list)

    for lid, state in learners.items():
        g = attributes.get(lid, {}).get(attribute_name)
        if g is None:
            continue
        for est in state.mastery.values():
            mastery[str(g)].append(float(est.mastery))

    for ev in events:
        if ev.get("event_type") == "tutoring.hint":
            lid = str(ev.get("learner_id") or "")
            g = attributes.get(lid, {}).get(attribute_name)
            if g is None:
                continue
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            level = payload.get("hint_level", ev.get("hint_level", 0))
            hints[str(g)].append(float(level or 0))

    dispatch_by_group: dict[str, list[str]] = defaultdict(list)
    expired_receipts: set[str] = set()
    for ev in events:
        lid = str(ev.get("learner_id") or "")
        g = attributes.get(lid, {}).get(attribute_name)
        if g is None:
            continue
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        if ev.get("event_type") == "scheduler.dispatch":
            rid = str(payload.get("receipt_id") or "")
            if rid:
                dispatch_by_group[str(g)].append(rid)
        elif ev.get("event_type") == "scheduler.consumed":
            if payload.get("outcome") == "expired":
                rid = str(payload.get("receipt_id") or "")
                if rid:
                    expired_receipts.add(rid)

    for g, rids in dispatch_by_group.items():
        if rids:
            expired_rates[g].append(
                sum(1 for r in rids if r in expired_receipts) / len(rids)
            )

    comparisons: list[GroupComparison] = []

    def pairwise(
        values: dict[str, list[float]], metric: str, threshold: float
    ) -> None:
        groups = sorted(g for g, v in values.items() if len(v) >= cfg.min_group_size)
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i], groups[j]
                va = sum(values[a]) / len(values[a])
                vb = sum(values[b]) / len(values[b])
                gap = va - vb
                comparisons.append(
                    GroupComparison(
                        attribute=attribute_name,
                        group_a=a,
                        group_b=b,
                        metric=metric,
                        value_a=round(va, 4),
                        value_b=round(vb, 4),
                        gap=round(gap, 4),
                        n_a=len(values[a]),
                        n_b=len(values[b]),
                        flagged=abs(gap) >= threshold,
                    )
                )

    pairwise(mastery, "mastery_mean", cfg.mastery_gap_threshold)
    pairwise(expired_rates, "dispatch_expired_rate", cfg.expired_rate_gap_threshold)
    pairwise(hints, "hint_level_mean", cfg.hint_level_gap_threshold)

    return FairnessAuditReport(
        window_start=str(window[0]),
        window_end=str(window[1]),
        comparisons=comparisons,
        flagged_count=sum(1 for c in comparisons if c.flagged),
        config=asdict(cfg),
    )
