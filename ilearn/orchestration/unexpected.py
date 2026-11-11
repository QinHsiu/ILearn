"""Non-expected state capture, checkpointing, and resume."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ilearn.core.schemas import OrchestrationEvent, SessionPhase, SessionState
from ilearn.orchestration.events import append_orchestration_event


def record_unexpected_state(
    session: SessionState,
    *,
    checkpoint_dir: Path,
    context: dict[str, Any],
    stage: SessionPhase,
    agent: str = "tutor",
) -> OrchestrationEvent:
    """Persist UNEXPECTED_STATE event + checkpoint snapshot for later resume."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    event = append_orchestration_event(
        session,
        agent=agent,
        stage=stage,
        reason="UNEXPECTED_STATE",
        input_payload=context,
        output_payload={"status": "paused"},
        kind="unexpected_state",
        ok=False,
        metadata={"context": context},
    )
    checkpoint_path = checkpoint_dir / f"{session.session_id}.unexpected.json"
    payload = {
        "session_id": session.session_id,
        "phase": session.phase.value if hasattr(session.phase, "value") else str(session.phase),
        "event_id": event.event_id,
        "context": context,
        "event": event.model_dump(mode="json"),
    }
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    session.metadata["last_unexpected_event_id"] = event.event_id
    session.metadata["unexpected_checkpoint"] = str(checkpoint_path)
    return event


def resume_session(
    session: SessionState,
    *,
    decision: str,
    note: str = "",
) -> OrchestrationEvent:
    """Append a resume event after teacher/developer injects a handling decision."""
    allowed = {"continue", "replan", "human_takeover"}
    if decision not in allowed:
        raise ValueError(f"decision must be one of {sorted(allowed)}")
    return append_orchestration_event(
        session,
        agent="orchestrator",
        stage=session.phase,
        reason=f"resume:{decision}",
        input_payload={"decision": decision, "note": note},
        output_payload={"resumed": True},
        kind="resume",
        ok=True,
        metadata={"decision": decision, "note": note},
    )


def list_unexpected_events(session: SessionState) -> list[OrchestrationEvent]:
    return [e for e in session.event_log if e.kind == "unexpected_state"]


def derailment_report(sessions: list[SessionState]) -> dict[str, object]:
    """Aggregate UNEXPECTED_STATE events as a reverse coverage metric."""
    by_grade: dict[str, int] = {}
    by_stage: dict[str, int] = {}
    by_knowledge: dict[str, int] = {}
    total = 0
    for session in sessions:
        grade_key = str(session.profile.grade)
        for event in list_unexpected_events(session):
            total += 1
            by_grade[grade_key] = by_grade.get(grade_key, 0) + 1
            stage = event.stage.value if hasattr(event.stage, "value") else str(event.stage)
            by_stage[stage] = by_stage.get(stage, 0) + 1
            meta = event.metadata or {}
            kid = str(meta.get("knowledge_id") or "unknown")
            by_knowledge[kid] = by_knowledge.get(kid, 0) + 1
    return {
        "total_unexpected": total,
        "sessions_scanned": len(sessions),
        "by_grade": by_grade,
        "by_stage": by_stage,
        "by_knowledge": by_knowledge,
    }


def persist_derailment_report(
    directory: Path,
    report: dict[str, object],
    *,
    filename: str = "derailment_latest.json",
) -> Path:
    """Write a JSON snapshot for dashboards / offline audit packs."""
    from ilearn.core.datetime_utils import utc_now

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    payload = {
        **report,
        "generated_at": utc_now().isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
