"""P2 win-bar: public mastery rigor view (beyond single mastery score)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.effectiveness import compute_metrics
from ilearn.core.schemas import SessionState


class MasteryPublicView(BaseModel):
    mastery_percent: int | None = None
    evidence_count: int = 0
    probe_gap_count: int = 0
    discounted_hint_correct: int = 0


def build_mastery_public_view(session: SessionState) -> MasteryPublicView:
    metrics = compute_metrics(session)
    post = metrics.post_assessment_score
    pre = metrics.pre_assessment_score
    current = post if post is not None else pre
    mastery_percent = int(round(current)) if current is not None else None

    evidence_count = len(session.evidence_log or [])

    probe_gap_count = 0
    if session.diagnosis is not None:
        for row in session.diagnosis.knowledge_mastery:
            # Weak or unstable after practice signals probe gap exposure need
            if row.level in {"weak", "unstable"}:
                probe_gap_count += 1

    discounted = 0
    for rows in (session.hint_interactions or {}).values():
        for row in rows:
            flag = getattr(row, "solved_after_hint", None)
            if flag is True:
                discounted += 1

    return MasteryPublicView(
        mastery_percent=mastery_percent,
        evidence_count=evidence_count,
        probe_gap_count=probe_gap_count,
        discounted_hint_correct=discounted,
    )


def mastery_public_as_dict(view: MasteryPublicView) -> dict[str, Any]:
    return view.model_dump()
