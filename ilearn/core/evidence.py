"""Helpers for recording and querying knowledge evidence on a session."""

from uuid import uuid4

from ilearn.core.schemas import KnowledgeEvidence, SessionState


def make_evidence_id() -> str:
    return uuid4().hex


def claim_refs(evidence_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    refs: list[str] = []
    for evidence_id in evidence_ids:
        if not evidence_id or evidence_id in seen:
            continue
        seen.add(evidence_id)
        refs.append(evidence_id)
    return refs


def _evidence_key(event: KnowledgeEvidence) -> tuple:
    return (
        event.session_id,
        event.item_id,
        event.knowledge_id,
        event.lane,
        event.step_index,
    )


def append_evidence(session: SessionState, event: KnowledgeEvidence) -> None:
    key = _evidence_key(event)
    if any(_evidence_key(e) == key for e in session.evidence_log):
        return
    session.evidence_log.append(event)


def events_for_knowledge(session: SessionState, knowledge_id: str) -> list[KnowledgeEvidence]:
    return [e for e in session.evidence_log if e.knowledge_id == knowledge_id]
