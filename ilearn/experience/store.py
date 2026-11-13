"""Experience store — read-only prior for decision points (no LLM / no online RL)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ilearn.experience.models import ExperiencePrior, ExperienceRecord

# Re-export for callers that import from store
__all__ = ["ExperienceRecord", "ExperiencePrior", "ExperienceStore"]


def _overlap_score(left: str, right: str) -> float:
    a = {t for t in left.casefold().replace("，", " ").replace(",", " ").split() if t}
    b = {t for t in right.casefold().replace("，", " ").replace(",", " ").split() if t}
    if not a or not b:
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

    @property
    def records(self) -> list[ExperienceRecord]:
        return list(self._records)

    def retrieve(
        self,
        segment: dict[str, Any] | None = None,
        situation: str | dict[str, Any] | None = None,
        *,
        min_support: int = 3,
        top_k: int = 5,
    ) -> ExperiencePrior | list[ExperienceRecord] | None:
        """Segment+situation aggregate prior, or legacy similarity list.

        New API (P2 redesign):
            retrieve({"stage": "k12", "skill": "frac"}, "hint_before_attempt")
            → ExperiencePrior | None (None when support < min_support)

        Legacy API (orchestrator):
            retrieve({"stage": "primary", "text": "..."}) → list[ExperienceRecord]
        """
        # Legacy: single dict with "text" / no exact situation string
        if situation is None and isinstance(segment, dict):
            if "text" in segment or "situation" not in segment or isinstance(
                segment.get("situation"), (dict, type(None))
            ):
                # Similarity path used by prior_for / old tests
                return self._retrieve_similar(segment, top_k=top_k)

        seg = segment or {}
        sit = situation if isinstance(situation, str) else str(
            (situation or {}).get("situation")
            or (situation or {}).get("text")
            or ""
        )
        if not sit and isinstance(segment, dict):
            sit = str(segment.get("situation") or "")

        pool = [
            r
            for r in self._records
            if (seg.get("stage") is None or r.learner_segment.get("stage") == seg.get("stage"))
            and (
                seg.get("skill") is None
                or r.learner_segment.get("skill") == seg.get("skill")
            )
            and r.situation == sit
        ]
        if len(pool) < min_support:
            return None

        tally: dict[str, Counter] = {}
        for r in pool:
            tally.setdefault(r.strategy, Counter())[r.outcome] += 1
        scored = sorted(
            tally.items(),
            key=lambda kv: kv[1]["effective"] - kv[1]["ineffective"],
            reverse=True,
        )
        best_strategy, counts = scored[0]
        support = sum(counts.values())
        confidence = max(0.0, (counts["effective"] - counts["ineffective"]) / support)
        refs = list(pool)
        return ExperiencePrior(
            situation=sit,
            recommended_strategy=best_strategy if confidence > 0 else None,
            confidence=round(confidence, 3),
            support=support,
            refs=refs,
            records=refs,
            experience_refs=[r.record_id for r in refs],
        )

    def _retrieve_similar(
        self, situation: dict[str, Any], top_k: int = 5
    ) -> list[ExperienceRecord]:
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

    def prior_for(
        self, situation: dict[str, Any], top_k: int = 5
    ) -> ExperiencePrior:
        """Legacy similarity prior for orchestrator decision context."""
        records = self._retrieve_similar(situation, top_k=top_k)
        return ExperiencePrior(
            situation=situation,
            records=records,
            refs=records,
            experience_refs=[r.record_id for r in records],
            support=len(records),
            confidence=1.0 if records else 0.0,
            recommended_strategy=records[0].strategy if records else None,
        )

    def hit_rate(self) -> dict[str, float | int]:
        """Aggregate outcome stats for `ilearn experience stats`."""
        total = len(self._records)
        if total == 0:
            return {"total": 0, "hit_rate": 0.0, "effective": 0, "ineffective": 0}
        effective = sum(1 for r in self._records if r.outcome == "effective")
        ineffective = sum(1 for r in self._records if r.outcome == "ineffective")
        judged = effective + ineffective
        return {
            "total": total,
            "effective": effective,
            "ineffective": ineffective,
            "neutral": total - judged,
            "hit_rate": round(effective / judged, 3) if judged else 0.0,
        }
