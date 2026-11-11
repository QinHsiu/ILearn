"""W6: session-close ritual — evidence-first today/tomorrow, never leak final answers."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ilearn.core.datetime_utils import utc_now
from ilearn.core.mastery_public import build_mastery_public_view
from ilearn.core.schemas import SessionState

HONESTY_NOTE = "提示后做对不计入掌握；收工卡不含终答。"
CLOSED_META_KEY = "session_closed_at"


class SessionCloseView(BaseModel):
    closed: bool
    closed_at: str | None = None
    headline: str
    next_challenge: str
    evidence_count: int = 0
    probe_gap_count: int = 0
    parent_line: str
    honesty_note: str = HONESTY_NOTE
    session_id: str | None = None
    forbidden: list[str] = Field(default_factory=list)


def _next_challenge(session: SessionState) -> str:
    overlay = session.metadata.get("student_summary") if isinstance(session.metadata, dict) else None
    if isinstance(overlay, dict) and overlay.get("next_challenge"):
        return str(overlay["next_challenge"])
    if session.diagnosis is not None:
        for row in session.diagnosis.knowledge_mastery:
            if row.level == "weak":
                return row.knowledge_name or row.knowledge_id
        if session.diagnosis.knowledge_mastery:
            first = session.diagnosis.knowledge_mastery[0]
            return first.knowledge_name or first.knowledge_id
    if session.plan is not None and session.plan.goal:
        return session.plan.goal
    return "继续今日挑战"


def _closed_at(session: SessionState) -> str | None:
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    raw = meta.get(CLOSED_META_KEY)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _redact(text: str, session: SessionState) -> str:
    out = text
    paper = session.paper
    if paper is not None:
        for item in paper.items:
            key = (item.answer_key or "").strip()
            if key:
                out = out.replace(key, "●●●")
    for banned in ("最终答案", "标准答案"):
        out = out.replace(banned, "终答已遮罩")
    return out


def stamp_session_close(session: SessionState) -> SessionState:
    """Idempotent close stamp. First close wins."""
    meta = dict(session.metadata or {})
    if not str(meta.get(CLOSED_META_KEY) or "").strip():
        meta[CLOSED_META_KEY] = utc_now().isoformat()
    session.metadata = meta
    return session


def build_session_close(session: SessionState) -> SessionCloseView:
    mastery = build_mastery_public_view(session)
    challenge = _redact(_next_challenge(session), session)
    closed_at = _closed_at(session)
    closed = bool(closed_at)
    if closed:
        headline = f"今天收工了 · 证据 {mastery.evidence_count} 条"
        parent_line = f"孩子今天收工了。下一挑战：{challenge}。不含终答。"
    else:
        headline = f"今天先到这里 · 证据 {mastery.evidence_count} 条"
        parent_line = f"孩子今天还没收工。下一挑战：{challenge}。"
    return SessionCloseView(
        closed=closed,
        closed_at=closed_at,
        headline=_redact(headline, session),
        next_challenge=challenge,
        evidence_count=mastery.evidence_count,
        probe_gap_count=mastery.probe_gap_count,
        parent_line=_redact(parent_line, session),
        honesty_note=HONESTY_NOTE,
        session_id=session.session_id,
    )
