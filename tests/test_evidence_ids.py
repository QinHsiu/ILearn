from ilearn.core.evidence import claim_refs, make_evidence_id
from ilearn.core.schemas import KnowledgeEvidence


def test_knowledge_evidence_has_unique_evidence_id():
    a = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="k1",
        lane="probe",
        correct=False,
    )
    b = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="k1",
        lane="probe",
        correct=False,
    )
    assert a.evidence_id
    assert a.evidence_id != b.evidence_id
    assert len(make_evidence_id()) >= 8


def test_claim_refs_deduplicates_preserving_order():
    ids = ["a1", "b2", "a1", "", "c3", "b2"]
    assert claim_refs(ids) == ["a1", "b2", "c3"]
