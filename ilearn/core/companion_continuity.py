"""P11 companion continuity across sessions for the same nickname."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.schemas import SessionState


class ContinuityDay(BaseModel):
    day_index: int
    focus: str
    session_id: str | None = None


class PortraitSnapshot(BaseModel):
    """Cross-session portrait digest for companion continuity."""

    student_key: str | None = None
    weak_knowledge: list[str] = Field(default_factory=list)
    avg_probe: float | None = None
    avg_practice: float | None = None
    frustration: float = 0.0
    hint_dependency: float = 0.0
    source_session_id: str | None = None


class ContinuityView(BaseModel):
    nickname: str
    session_count: int = 0
    streak_days: int = 0
    next_challenge: str = "继续今日挑战"
    recent_session_ids: list[str] = Field(default_factory=list)
    seven_day_chain: list[ContinuityDay] = Field(default_factory=list)
    portrait_snapshot: PortraitSnapshot | None = None
    latest_replan_explain: dict[str, Any] | None = None


def _session_stamp(session: SessionState) -> datetime:
    if session.paper is not None and session.paper.created_at is not None:
        ts = session.paper.created_at
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    return datetime.min.replace(tzinfo=timezone.utc)


def _next_challenge_from(session: SessionState) -> str:
    overlay = session.metadata.get("student_summary")
    if isinstance(overlay, dict) and overlay.get("next_challenge"):
        return str(overlay["next_challenge"])
    if session.diagnosis is not None:
        for row in session.diagnosis.knowledge_mastery:
            if row.level == "weak":
                return row.knowledge_name or row.knowledge_id
    if session.plan is not None and session.plan.goal:
        return session.plan.goal
    return "继续今日挑战"


def _portrait_snapshot(session: SessionState) -> PortraitSnapshot | None:
    portrait = session.portrait
    if portrait is None:
        # Fall back to diagnosis weak list
        weak: list[str] = []
        if session.diagnosis is not None:
            for row in session.diagnosis.knowledge_mastery or []:
                if row.level in {"weak", "unstable"}:
                    weak.append(row.knowledge_name or row.knowledge_id)
        if not weak:
            return None
        return PortraitSnapshot(
            weak_knowledge=weak[:5],
            source_session_id=session.session_id,
        )

    probes = [r.probe_mastery for r in portrait.mastery_records.values()]
    practices = [r.practice_score for r in portrait.mastery_records.values()]
    weak_from_state = sorted(
        portrait.knowledge_state.items(),
        key=lambda kv: kv[1],
    )[:5]
    weak_names = [k for k, _ in weak_from_state]
    if session.diagnosis is not None:
        named = []
        by_id = {
            km.knowledge_id: km.knowledge_name or km.knowledge_id
            for km in session.diagnosis.knowledge_mastery or []
        }
        for kid in weak_names:
            named.append(by_id.get(kid, kid))
        weak_names = named or weak_names

    return PortraitSnapshot(
        student_key=portrait.student_key,
        weak_knowledge=weak_names[:5],
        avg_probe=(sum(probes) / len(probes)) if probes else None,
        avg_practice=(sum(practices) / len(practices)) if practices else None,
        frustration=float(portrait.dimensions.emotional.get("frustration", 0.0) or 0.0),
        hint_dependency=float(
            portrait.dimensions.behavioral.get("hint_dependency", 0.0) or 0.0
        ),
        source_session_id=session.session_id,
    )


def build_learner_continuity(
    nickname: str,
    sessions: list[SessionState],
) -> ContinuityView:
    name = (nickname or "").strip() or "学习者"
    ordered = sorted(sessions, key=_session_stamp, reverse=True)
    recent_ids = [s.session_id for s in ordered[:7]]
    next_challenge = (
        _next_challenge_from(ordered[0]) if ordered else "完成首次测评开启陪伴"
    )

    days = sorted(
        {
            _session_stamp(s).date()
            for s in ordered
            if _session_stamp(s) != datetime.min.replace(tzinfo=timezone.utc)
        },
        reverse=True,
    )
    streak = 0
    if days:
        streak = 1
        for i in range(1, len(days)):
            if (days[i - 1] - days[i]).days == 1:
                streak += 1
            else:
                break

    chain: list[ContinuityDay] = []
    for i in range(1, 8):
        sess = ordered[i - 1] if i - 1 < len(ordered) else None
        focus = _next_challenge_from(sess) if sess else f"第 {i} 日待开启"
        chain.append(
            ContinuityDay(
                day_index=i,
                focus=focus,
                session_id=sess.session_id if sess else None,
            )
        )

    snapshot = _portrait_snapshot(ordered[0]) if ordered else None
    replan_explain = None
    if ordered:
        raw = (ordered[0].metadata or {}).get("replan_explain")
        if isinstance(raw, dict):
            replan_explain = raw

    return ContinuityView(
        nickname=name,
        session_count=len(ordered),
        streak_days=streak,
        next_challenge=next_challenge,
        recent_session_ids=recent_ids,
        seven_day_chain=chain,
        portrait_snapshot=snapshot,
        latest_replan_explain=replan_explain,
    )


def continuity_as_dict(view: ContinuityView) -> dict[str, Any]:
    return view.model_dump()
