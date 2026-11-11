"""Append-only orchestration events and span-tree derivation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ilearn.core.schemas import (
    AgentDecision,
    OrchestrationEvent,
    SessionPhase,
    SessionState,
)


def digest_payload(payload: Any) -> str:
    """Stable SHA-256 hex digest of a JSON-serializable payload."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def event_content_hash(event: OrchestrationEvent) -> str:
    """Hash of the event body excluding the content_hash field itself."""
    body = {
        "event_id": event.event_id,
        "kind": event.kind,
        "agent": event.agent,
        "stage": event.stage.value if hasattr(event.stage, "value") else str(event.stage),
        "reason": event.reason,
        "input_digest": event.input_digest,
        "output_digest": event.output_digest,
        "span_id": event.span_id,
        "parent_span_id": event.parent_span_id,
        "ts": event.ts.isoformat() if hasattr(event.ts, "isoformat") else str(event.ts),
        "ok": event.ok,
        "degraded": event.degraded,
        "evidence_ids": list(event.evidence_ids),
        "metadata": event.metadata,
    }
    return digest_payload(body)


def append_orchestration_event(
    session: SessionState,
    *,
    agent: str,
    stage: SessionPhase,
    reason: str = "",
    input_payload: Any | None = None,
    output_payload: Any | None = None,
    ok: bool = True,
    degraded: bool = False,
    evidence_ids: list[str] | None = None,
    kind: str = "decision",
    parent_span_id: str | None = None,
    parent_hint_stage: SessionPhase | None = None,
    metadata: dict[str, Any] | None = None,
) -> OrchestrationEvent:
    """Append an immutable event and dual-write a compatible AgentDecision."""
    stage_span_id = _ensure_stage_span(session, stage)
    parent = parent_span_id or stage_span_id
    if parent_hint_stage is not None:
        parent = _ensure_stage_span(session, parent_hint_stage)

    event = OrchestrationEvent(
        kind=kind,
        agent=agent,
        stage=stage,
        reason=reason,
        input_digest=digest_payload(input_payload or {}),
        output_digest=digest_payload(output_payload or {}),
        parent_span_id=parent,
        ok=ok,
        degraded=degraded,
        evidence_ids=list(evidence_ids or []),
        metadata=dict(metadata or {}),
    )
    event.content_hash = event_content_hash(event)
    session.event_log.append(event)

    if kind == "decision":
        session.decision_log.append(
            AgentDecision(
                agent=agent,
                phase=stage,
                reason=reason,
                evidence_ids=list(evidence_ids or []),
                ok=ok,
                degraded=degraded,
            )
        )
    return event


def _ensure_stage_span(session: SessionState, stage: SessionPhase) -> str:
    stage_value = stage.value if hasattr(stage, "value") else str(stage)
    for event in session.event_log:
        if event.kind == "stage_span" and event.stage == stage:
            return event.span_id
    marker = OrchestrationEvent(
        kind="stage_span",
        agent="orchestrator",
        stage=stage,
        reason=f"stage:{stage_value}",
        parent_span_id=None,
    )
    marker.content_hash = event_content_hash(marker)
    session.event_log.append(marker)
    return marker.span_id


def build_span_tree(events: list[OrchestrationEvent]) -> dict[str, Any]:
    """Build an OpenTelemetry-inspired span tree from orchestration events."""
    by_id: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for event in events:
        stage_name = event.stage.value if hasattr(event.stage, "value") else str(event.stage)
        node = {
            "span_id": event.span_id,
            "parent_span_id": event.parent_span_id,
            "kind": "stage" if event.kind == "stage_span" else "agent",
            "name": stage_name if event.kind == "stage_span" else event.agent,
            "stage": stage_name,
            "event_kind": event.kind,
            "reason": event.reason,
            "input_hash": event.input_digest,
            "output_hash": event.output_digest,
            "ok": event.ok,
            "degraded": event.degraded,
            "ts": event.ts.isoformat() if hasattr(event.ts, "isoformat") else str(event.ts),
            "children": [],
        }
        by_id[event.span_id] = node

    for node in by_id.values():
        parent_id = node["parent_span_id"]
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return {
        "kind": "session",
        "name": "session",
        "children": roots,
    }
