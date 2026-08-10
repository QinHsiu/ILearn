"""Deterministic mastery updates from knowledge evidence events."""

from __future__ import annotations

from ilearn.core.schemas import KnowledgeEvidence, LearnerPortrait, MasteryRecord


def _ema(current: float, observed: float, *, alpha: float) -> float:
    return max(0.0, min(1.0, current * (1.0 - alpha) + observed * alpha))


def mastery_stars(score: float) -> int:
    return max(0, min(5, round(score * 5)))


def mastery_confidence(evidence_count: int) -> float:
    return min(1.0, 0.2 + 0.1 * evidence_count)


def apply_evidence_to_mastery(
    portrait: LearnerPortrait,
    events: list[KnowledgeEvidence],
    *,
    alpha: float = 0.3,
) -> LearnerPortrait:
    for ev in events:
        rec = portrait.mastery_records.get(ev.knowledge_id) or MasteryRecord()
        observed = 1.0 if ev.correct else 0.0
        observed *= ev.confidence
        if ev.lane == "probe":
            rec.probe_mastery = _ema(rec.probe_mastery, observed, alpha=alpha)
            rec.last_probe_at = ev.created_at
        else:
            rec.practice_score = _ema(rec.practice_score, observed, alpha=alpha)
        rec.evidence_count += 1
        portrait.mastery_records[ev.knowledge_id] = rec
        portrait.knowledge_state[ev.knowledge_id] = max(
            rec.practice_score, rec.probe_mastery
        )
    return portrait
