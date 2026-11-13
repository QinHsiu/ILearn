"""Offline extraction of ExperienceRecord triples from event_log (read-only)."""

from __future__ import annotations

from typing import Any

from ilearn.experience.models import ExperienceRecord


def extract_experiences(events: list[dict[str, Any]]) -> list[ExperienceRecord]:
    """Extract (situation → strategy → outcome) from tutoring.hint + grade/diagnosis."""
    records: list[ExperienceRecord] = []
    hint_by_session: dict[str, dict[str, Any]] = {}
    for ev in events:
        etype = ev.get("event_type") or ev.get("kind")
        if etype == "tutoring.hint":
            sid = str(ev.get("session_id") or "")
            if sid:
                hint_by_session[sid] = ev
        elif etype in ("grade.completed", "diagnosis.completed"):
            sid = str(ev.get("session_id") or "")
            hint = hint_by_session.get(sid)
            if not hint:
                continue
            outcome = _classify_outcome(ev)
            hint_eid = str(hint.get("event_id") or "")
            ev_eid = str(ev.get("event_id") or "")
            records.append(
                ExperienceRecord(
                    record_id=f"exp-{ev_eid or len(records)}",
                    learner_segment={
                        "stage": ev.get("life_stage", "k12"),
                        "grade": ev.get("grade"),
                        "skill": ev.get("skill_id"),
                    },
                    situation=(
                        f"{hint.get('trigger', 'unknown')}_before_"
                        f"{hint.get('phase', 'practice')}"
                    ),
                    strategy=f"hint_level_{hint.get('hint_level', 0)}",
                    outcome=outcome,  # type: ignore[arg-type]
                    evidence_refs=[x for x in (hint_eid, ev_eid) if x],
                    created_at=str(ev.get("occurred_at") or ""),
                )
            )
    return records


def _classify_outcome(ev: dict[str, Any]) -> str:
    etype = ev.get("event_type") or ev.get("kind")
    if etype == "diagnosis.completed":
        return "effective" if float(ev.get("mastery_delta") or 0) > 0.05 else "neutral"
    return "effective" if float(ev.get("score") or 0) >= 0.8 else "ineffective"
