"""Experience store — read-only prior for decision points (no online RL)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExperienceRecord(BaseModel):
    record_id: str
    learner_segment: dict[str, Any] = Field(default_factory=dict)
    situation: str
    strategy: str
    outcome: Literal["effective", "ineffective", "neutral"] = "neutral"
    evidence_refs: list[str] = Field(default_factory=list)


class ExperiencePrior(BaseModel):
    """Injected into AgentContext.metadata; never selects the action itself."""

    situation: dict[str, Any] = Field(default_factory=dict)
    records: list[ExperienceRecord] = Field(default_factory=list)
    experience_refs: list[str] = Field(default_factory=list)


def _overlap_score(left: str, right: str) -> float:
    a = {t for t in left.casefold().replace("，", " ").replace(",", " ").split() if t}
    b = {t for t in right.casefold().replace("，", " ").replace(",", " ").split() if t}
    if not a or not b:
        # Character bigram fallback for CJK without spaces
        def bigrams(s: str) -> set[str]:
            s = s.casefold()
            return {s[i : i + 2] for i in range(max(0, len(s) - 1))}

        ba, bb = bigrams(left), bigrams(right)
        if not ba or not bb:
            return 0.0
        return len(ba & bb) / len(ba | bb)
    return len(a & b) / len(a | b)


class ExperienceStore:
    def __init__(self, records: list[ExperienceRecord] | None = None) -> None:
        self._records = list(records or [])

    def add(self, record: ExperienceRecord) -> None:
        self._records.append(record)

    def retrieve(self, situation: dict[str, Any], top_k: int = 5) -> list[ExperienceRecord]:
        """Coarse segment filter then situation similarity. Read-only."""
        stage = situation.get("stage")
        candidates = [
            r
            for r in self._records
            if stage is None or r.learner_segment.get("stage") == stage
        ]
        text = str(situation.get("text") or situation.get("situation") or "")
        scored = sorted(
            candidates,
            key=lambda r: _overlap_score(r.situation, text),
            reverse=True,
        )
        return scored[:top_k]

    def prior_for(self, situation: dict[str, Any], top_k: int = 5) -> ExperiencePrior:
        records = self.retrieve(situation, top_k=top_k)
        return ExperiencePrior(
            situation=situation,
            records=records,
            experience_refs=[r.record_id for r in records],
        )
