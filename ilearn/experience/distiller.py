"""OMCE-style distillation trigger — when episodic patterns stabilize (no LLM)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ilearn.experience.models import ExperienceRecord


def distill_candidates(
    records: list[ExperienceRecord],
    *,
    min_episodic: int = 5,
    stable_ratio: float = 0.7,
) -> list[ExperienceRecord]:
    """当某（签名前缀, strategy）的 episodic 记录达到阈值且结果稳定时，产出 distilled。"""
    groups: dict[tuple, list[ExperienceRecord]] = defaultdict(list)
    for r in records:
        if r.form != "episodic":
            continue
        key = (
            tuple(r.structural_signature[:2]),
            r.strategy,
            r.learner_segment.get("stage"),
        )
        groups[key].append(r)

    distilled: list[ExperienceRecord] = []
    for (sig_prefix, strategy, _stage), group in groups.items():
        if len(group) < min_episodic:
            continue
        outcomes = [r.outcome for r in group]
        dominant = max(set(outcomes), key=outcomes.count)
        if outcomes.count(dominant) / len(outcomes) < stable_ratio:
            continue
        created_ats = [_as_dt(r.created_at) for r in group]
        created_ats = [c for c in created_ats if c is not None]
        distilled.append(
            ExperienceRecord(
                record_id=f"dist-{group[0].record_id}",
                learner_segment=dict(group[0].learner_segment),
                situation=group[0].situation,
                structural_signature=list(sig_prefix),
                strategy=strategy,
                outcome=dominant,  # type: ignore[arg-type]
                form="distilled",
                evidence_refs=[r.record_id for r in group],
                created_at=max(created_ats) if created_ats else group[0].created_at,
                state_version_at_creation=max(
                    int(r.state_version_at_creation) for r in group
                ),
                derived_from=[r.record_id for r in group],
            )
        )
    return distilled


def _as_dt(value: datetime | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
