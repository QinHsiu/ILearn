"""Helpers for recording and querying knowledge evidence on a session."""

from ilearn.core.schemas import KnowledgeEvidence, SessionState


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
