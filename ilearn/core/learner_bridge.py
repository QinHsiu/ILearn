"""Bridge session diagnosis/evidence → hash-chained StateEvents."""

from __future__ import annotations

from ilearn.core.datetime_utils import utc_now
from ilearn.core.schemas import SessionState, StudentProfile
from ilearn.core.state_event import StateEvent


def resolve_learner_id(profile: StudentProfile, *, fallback: str | None = None) -> str:
    nick = (profile.nickname or "").strip()
    if nick:
        return f"nick:{nick}"
    if fallback:
        return fallback
    return f"anon:{profile.region}:{profile.grade}:{profile.age}"


def events_from_diagnosis(session: SessionState) -> list[StateEvent]:
    """Project diagnosis mastery + error tags into state events (unordered drafts)."""
    if session.diagnosis is None:
        return []
    learner_id = resolve_learner_id(session.profile, fallback=session.session_id)
    ts = utc_now().isoformat()
    out: list[StateEvent] = []
    for row in session.diagnosis.knowledge_mastery:
        out.append(
            StateEvent(
                learner_id=learner_id,
                event_type="mastery.update",
                payload={
                    "skill_id": row.knowledge_id,
                    "mastery": float(row.score_rate),
                    "timestamp": ts,
                    "source_session": session.session_id,
                },
            )
        )
        for tag, count in (row.error_tag_counts or {}).items():
            if count <= 0:
                continue
            out.append(
                StateEvent(
                    learner_id=learner_id,
                    event_type="misconception.detected",
                    payload={
                        "code": str(tag),
                        "description": f"{row.knowledge_name or row.knowledge_id}:{tag}",
                        "timestamp": ts,
                        "source_session": session.session_id,
                    },
                )
            )
    return out


def events_from_engagement(session: SessionState, **signals) -> list[StateEvent]:
    learner_id = resolve_learner_id(session.profile, fallback=session.session_id)
    payload = {
        "loop_count": session.loop_count,
        "phase": str(session.phase.value if hasattr(session.phase, "value") else session.phase),
        "session_id": session.session_id,
        **signals,
    }
    return [
        StateEvent(
            learner_id=learner_id,
            event_type="engagement.updated",
            payload=payload,
        )
    ]
