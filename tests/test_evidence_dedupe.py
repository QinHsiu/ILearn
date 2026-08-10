from ilearn.core.evidence import append_evidence
from ilearn.core.schemas import KnowledgeEvidence, SessionState, StudentProfile


def test_append_evidence_dedupes_same_key():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    ev = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="probe",
        correct=True,
        step_index=0,
    )
    append_evidence(session, ev)
    append_evidence(session, ev.model_copy())
    assert len(session.evidence_log) == 1
