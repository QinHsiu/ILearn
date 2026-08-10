"""Practice vs probe mastery gap metrics (OPT-074)."""

from __future__ import annotations

from ilearn.core.schemas import LearnerPortrait


def compute_gap(practice: float, probe: float) -> float:
    return practice - probe


def gap_exceeds(*, practice: float, probe: float, threshold: float = 0.25) -> bool:
    return compute_gap(practice, probe) > threshold


def gap_flag(portrait: LearnerPortrait, *, threshold: float = 0.25) -> list[str]:
    flags: list[str] = []
    for rec in portrait.mastery_records.values():
        if gap_exceeds(practice=rec.practice_score, probe=rec.probe_mastery, threshold=threshold):
            flags.append("practice_probe_gap")
            break
    return flags
