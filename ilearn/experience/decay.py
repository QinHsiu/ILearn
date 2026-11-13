"""Time / version decay pure functions for experience ranking (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecayConfig:
    half_life_days: float = 90.0
    version_penalty_per_step: float = 0.02


def time_weight(age_days: float, cfg: DecayConfig | None = None) -> float:
    """指数衰减：0.5 ** (age/half_life)。age<=0 时为 1。"""
    cfg = cfg or DecayConfig()
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / cfg.half_life_days)


def version_weight(distance: int, cfg: DecayConfig | None = None) -> float:
    cfg = cfg or DecayConfig()
    return max(0.0, 1.0 - cfg.version_penalty_per_step * abs(int(distance)))


def combined_score(
    confidence: float,
    age_days: float,
    version_distance: int,
    cfg: DecayConfig | None = None,
) -> float:
    cfg = cfg or DecayConfig()
    return float(confidence) * time_weight(age_days, cfg) * version_weight(version_distance, cfg)
