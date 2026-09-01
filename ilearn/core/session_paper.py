"""Resolve assessment paper from session state (including adaptive anchor)."""

from __future__ import annotations

from ilearn.core.schemas import AssessmentPaper, SessionState


def adaptive_anchor_paper(session: SessionState) -> AssessmentPaper | None:
    """Anchor paper kept in metadata during cold-start adaptive assessment."""
    adaptive = session.metadata.get("adaptive")
    if not isinstance(adaptive, dict):
        return None
    raw = adaptive.get("anchor_paper")
    if not isinstance(raw, dict):
        return None
    items = raw.get("items")
    if not isinstance(items, list) or not items:
        return None
    try:
        return AssessmentPaper.model_validate(raw)
    except Exception:
        return None


def has_assessment_paper(session: SessionState) -> bool:
    return session.paper is not None or adaptive_anchor_paper(session) is not None


def paper_for_tutor(session: SessionState) -> AssessmentPaper | None:
    if session.paper is not None:
        return session.paper
    return adaptive_anchor_paper(session)
