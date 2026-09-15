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
    """Update mastery; hinted corrects never raise probe_mastery (P2 win-bar)."""
    for ev in events:
        rec = portrait.mastery_records.get(ev.knowledge_id) or MasteryRecord()
        observed = 1.0 if ev.correct else 0.0
        observed *= ev.confidence
        hinted = bool(ev.hint_level and ev.hint_level != "none")
        if ev.lane == "probe" and not hinted:
            rec.probe_mastery = _ema(rec.probe_mastery, observed, alpha=alpha)
            rec.last_probe_at = ev.created_at
        else:
            # practice lane, or probe-with-hint → discounted practice only
            practice_obs = observed * (0.5 if hinted and ev.correct else 1.0)
            rec.practice_score = _ema(rec.practice_score, practice_obs, alpha=alpha)
        rec.evidence_count += 1
        portrait.mastery_records[ev.knowledge_id] = rec
        # Mastered signal prefers unassisted probe; never treat hinted success as mastery peak
        if hinted and ev.correct:
            portrait.knowledge_state[ev.knowledge_id] = rec.practice_score
        else:
            portrait.knowledge_state[ev.knowledge_id] = max(
                rec.practice_score, rec.probe_mastery
            )
    return portrait


def assert_hint_correct_does_not_raise_probe(
    before: MasteryRecord,
    after: MasteryRecord,
) -> None:
    """Helper for P2 tests."""
    assert after.probe_mastery <= before.probe_mastery + 1e-9

