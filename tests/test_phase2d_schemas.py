from ilearn.core.schemas import AgentDecision, PendingQuestion, SessionPhase, SessionState, StudentProfile


def test_agent_decision_defaults():
    d = AgentDecision(agent="diagnosis", phase=SessionPhase.DIAGNOSE, reason="ok")
    assert d.ok is True and d.degraded is False and d.evidence_ids == []


def test_session_has_decision_and_pending_lists():
    s = SessionState(
        session_id="s1",
        profile=StudentProfile(region="beijing", grade=5, age=11),
    )
    assert s.decision_log == []
    assert s.pending_questions == []
    s.pending_questions.append(
        PendingQuestion(question_id="q1", expected_answer="42", paper_id="p1")
    )
    assert s.pending_questions[0].expected_answer == "42"
