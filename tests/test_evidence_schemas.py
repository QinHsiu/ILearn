from ilearn.core.evidence import append_evidence, events_for_knowledge
from ilearn.core.schemas import (
    KnowledgeEvidence,
    SessionPhase,
    SessionState,
    StepAttempt,
    StepVerdict,
    StudentProfile,
)


def test_step_attempt_aligns_rubric_index():
    StepAttempt(
        item_id="q1",
        step_index=0,
        step_text="列式",
        student_expression="12+8",
        lane="practice",
    )


def test_step_verdict_defaults():
    v = StepVerdict(step_index=0, status="correct")
    assert v.comment == ""


def test_knowledge_evidence_requires_session():
    ev = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="practice",
        correct=False,
        error_tag="calc_error",
        hint_level="none",
        confidence=0.9,
    )
    assert ev.lane == "practice"


def test_session_state_defaults_evidence_log():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    assert session.evidence_log == []


def test_session_state_deserializes_without_evidence_log():
    payload = {
        "session_id": "legacy-s1",
        "profile": {"region": "北京", "grade": 5, "age": 11},
        "phase": SessionPhase.ONBOARD.value,
    }
    session = SessionState.model_validate(payload)
    assert session.evidence_log == []


def test_append_evidence_and_events_for_knowledge():
    session = SessionState(
        session_id="s1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )
    ev1 = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="practice",
        correct=True,
    )
    ev2 = KnowledgeEvidence(
        session_id="s1",
        item_id="q2",
        knowledge_id="frac_add_diff",
        lane="probe",
        correct=False,
        error_tag="concept_gap",
    )
    append_evidence(session, ev1)
    append_evidence(session, ev2)

    assert len(session.evidence_log) == 2
    assert events_for_knowledge(session, "frac_add_same") == [ev1]
    assert events_for_knowledge(session, "frac_add_diff") == [ev2]
    assert events_for_knowledge(session, "missing") == []
