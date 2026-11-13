"""Experience store — read-only prior for decision points (no LLM / no online RL)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ilearn.experience.decay import DecayConfig, combined_score, time_weight
from ilearn.experience.models import ExperiencePrior, ExperienceRecord
from ilearn.experience.signature import StructuralSignature

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


def _as_dt(value: datetime | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class ExperienceStore:
    def __init__(
        self,
        records: list[ExperienceRecord] | None = None,
        cfg: DecayConfig | None = None,
    ) -> None:
        self._records = list(records or [])
        self._cfg = cfg or DecayConfig()

    def add(self, record: ExperienceRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> list[ExperienceRecord]:
        return list(self._records)

    def retrieve(
        self,
        segment: dict[str, Any] | None = None,
        situation: str | dict[str, Any] | None = None,
        current_state_version: int | None = None,
        now: datetime | None = None,
        signature: StructuralSignature | None = None,
        *,
        min_support: int = 3,
        top_k: int = 5,
        structural_prefix: int = 2,
    ) -> ExperiencePrior | list[ExperienceRecord] | None:
        """两阶段检索：结构签名粗筛 → 时间/版本/form 精排；无 signature 时退化为语义检索。"""
        if situation is None and isinstance(segment, dict):
            if "text" in segment or "situation" not in segment or isinstance(
                segment.get("situation"), (dict, type(None))
            ):
                return self._retrieve_similar(segment, top_k=top_k)

        seg = segment or {}
        sit = (
            situation
            if isinstance(situation, str)
            else str(
                (situation or {}).get("situation")
                or (situation or {}).get("text")
                or ""
            )
        )
        if not sit and isinstance(segment, dict):
            sit = str(segment.get("situation") or "")

        now_aware = now or datetime.now(timezone.utc)
        if now_aware.tzinfo is None:
            now_aware = now_aware.replace(tzinfo=timezone.utc)

        pool = [
            r
            for r in self._records
            if (seg.get("stage") is None or r.learner_segment.get("stage") == seg.get("stage"))
            and (
                seg.get("skill") is None
                or r.learner_segment.get("skill") == seg.get("skill")
            )
            and r.situation == sit
            and (
                r.valid_until is None
                or _as_dt(r.valid_until) is None
                or _as_dt(r.valid_until) > now_aware
            )
        ]

        structural_fallback = False
        if signature is not None:
            prefix = list(signature.tokens[:structural_prefix])
            structural = [
                r
                for r in pool
                if list(r.structural_signature[:structural_prefix]) == prefix
            ]
            if len(structural) >= min_support:
                pool = structural
            else:
                structural_fallback = True

        if len(pool) < min_support:
            return None

        if current_state_version is None and now is None and signature is None:
            prior = self._aggregate_static(sit, pool)
            prior.structural_fallback = structural_fallback
            return prior

        version = int(current_state_version or 0)
        scores: dict[str, float] = {}
        counts: dict[str, int] = {}
        recency: dict[str, list[float]] = {}
        for r in pool:
            created = _as_dt(r.created_at) or now_aware
            age = (now_aware - created).total_seconds() / 86400.0
            vdist = version - int(r.state_version_at_creation)
            sign = {
                "effective": 1.0,
                "ineffective": -1.0,
                "neutral": 0.0,
            }.get(r.outcome, 0.0)
            form_weight = 1.5 if r.form == "distilled" else 1.0
            w = combined_score(1.0, age, vdist, self._cfg) * sign * form_weight
            scores[r.strategy] = scores.get(r.strategy, 0.0) + w
            counts[r.strategy] = counts.get(r.strategy, 0) + 1
            recency.setdefault(r.strategy, []).append(time_weight(age, self._cfg))

        best = max(scores, key=scores.get)
        support = counts[best]
        raw_conf = max(0.0, scores[best] / support)
        avg_recency = sum(recency[best]) / len(recency[best])
        best_refs = [r for r in pool if r.strategy == best]
        version_distance = version - min(
            int(r.state_version_at_creation) for r in best_refs
        )
        return ExperiencePrior(
            situation=sit,
            recommended_strategy=best if raw_conf > 0 else None,
            confidence=round(raw_conf, 3),
            weighted_confidence=round(raw_conf * avg_recency, 3),
            support=support,
            recency_score=round(avg_recency, 3),
            version_distance=version_distance,
            refs=best_refs,
            records=best_refs,
            experience_refs=[r.record_id for r in best_refs],
            structural_fallback=structural_fallback,
        )

    def _aggregate_static(self, sit: str, pool: list[ExperienceRecord]) -> ExperiencePrior:
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
            weighted_confidence=round(confidence, 3),
            support=support,
            recency_score=1.0,
            version_distance=0,
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
        records = self._retrieve_similar(situation, top_k=top_k)
        return ExperiencePrior(
            situation=situation,
            records=records,
            refs=records,
            experience_refs=[r.record_id for r in records],
            support=len(records),
            confidence=1.0 if records else 0.0,
            weighted_confidence=1.0 if records else 0.0,
            recommended_strategy=records[0].strategy if records else None,
        )

    def hit_rate(
        self,
        *,
        weighted: bool = False,
        by_form: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        total = len(self._records)
        if total == 0:
            return {"total": 0, "hit_rate": 0.0, "effective": 0, "ineffective": 0}
        effective = sum(1 for r in self._records if r.outcome == "effective")
        ineffective = sum(1 for r in self._records if r.outcome == "ineffective")
        judged = effective + ineffective
        report: dict[str, Any] = {
            "total": total,
            "effective": effective,
            "ineffective": ineffective,
            "neutral": total - judged,
            "hit_rate": round(effective / judged, 3) if judged else 0.0,
        }
        if by_form:
            forms: dict[str, dict[str, int]] = {}
            for r in self._records:
                bucket = forms.setdefault(r.form, {"count": 0, "effective": 0})
                bucket["count"] += 1
                if r.outcome == "effective":
                    bucket["effective"] += 1
            report["by_form"] = forms
        if weighted:
            now_aware = now or datetime.now(timezone.utc)
            if now_aware.tzinfo is None:
                now_aware = now_aware.replace(tzinfo=timezone.utc)
            w_eff = 0.0
            w_ineff = 0.0
            for r in self._records:
                created = _as_dt(r.created_at) or now_aware
                age = (now_aware - created).total_seconds() / 86400.0
                tw = time_weight(age, self._cfg)
                if r.outcome == "effective":
                    w_eff += tw
                elif r.outcome == "ineffective":
                    w_ineff += tw
            denom = w_eff + w_ineff
            report["weighted_hit_rate"] = round(w_eff / denom, 3) if denom else 0.0
            report["half_life_days"] = self._cfg.half_life_days
        return report
