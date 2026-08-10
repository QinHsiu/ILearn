"""Helpers for recording and querying knowledge evidence on a session."""

from ilearn.core.schemas import KnowledgeEvidence, SessionState


def append_evidence(session: SessionState, event: KnowledgeEvidence) -> None:
    session.evidence_log.append(event)


def events_for_knowledge(session: SessionState, knowledge_id: str) -> list[KnowledgeEvidence]:
    return [e for e in session.evidence_log if e.knowledge_id == knowledge_id]
