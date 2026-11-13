"""Experience→strategy feedback weights — pure counters (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

StrategyOutcome = Literal["positive", "negative", "neutral"]


@dataclass
class StrategyWeight:
    strategy: str
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    last_updated: datetime | None = None

    @property
    def effectiveness(self) -> float:
        total = self.positive + self.negative
        return self.positive / total if total > 0 else 0.5

    @property
    def confidence(self) -> float:
        total = self.positive + self.negative + self.neutral
        return min(1.0, total / 20.0)

    def update(self, outcome: StrategyOutcome) -> None:
        setattr(self, outcome, getattr(self, outcome) + 1)
        self.last_updated = datetime.now(timezone.utc)


class ExperienceFeedbackRouter:
    def __init__(self) -> None:
        self._weights: dict[str, StrategyWeight] = {}

    def observe(self, strategy: str, outcome: StrategyOutcome) -> None:
        self._weights.setdefault(strategy, StrategyWeight(strategy)).update(outcome)

    def get_weight(self, strategy: str) -> float:
        w = self._weights.get(strategy)
        if w is None:
            return 1.0
        return 1.0 - w.confidence * (1.0 - w.effectiveness)

    def snapshot(self) -> dict:
        return {
            s: {
                "positive": w.positive,
                "negative": w.negative,
                "neutral": w.neutral,
                "effectiveness": round(w.effectiveness, 3),
                "confidence": round(w.confidence, 3),
            }
            for s, w in self._weights.items()
        }
