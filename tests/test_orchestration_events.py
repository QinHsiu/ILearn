"""Event-sourced orchestration log + span derivation."""

from __future__ import annotations

from ilearn.core.schemas import AgentDecision, OrchestrationEvent, SessionPhase, SessionState, StudentProfile
from ilearn.orchestration.backend import HostStateMachineBackend, LangGraphBackend, get_default_backend
from ilearn.orchestration.events import (
    append_orchestration_event,
    build_span_tree,
    digest_payload,
    event_content_hash,
)


def _session() -> SessionState:
    return SessionState(
        session_id="s-evt-1",
        profile=StudentProfile(region="北京", grade=5, age=11),
    )


def test_digest_payload_is_stable_sha256_hex():
    a = digest_payload({"item_id": "q1", "answer": "1/2"})
    b = digest_payload({"answer": "1/2", "item_id": "q1"})
    assert a == b
    assert len(a) == 64


def test_append_orchestration_event_dual_writes_decision_log():
    session = _session()
    event = append_orchestration_event(
        session,
        agent="practice",
        stage=SessionPhase.GRADE,
        reason="graded paper",
        input_payload={"n_answers": 1},
        output_payload={"n_grades": 1},
        ok=True,
    )
    assert isinstance(event, OrchestrationEvent)
    assert event.content_hash == event_content_hash(event)
    assert any(e.kind == "decision" and e.agent == "practice" for e in session.event_log)
    assert any(e.kind == "stage_span" for e in session.event_log)
    assert len(session.decision_log) == 1
    assert session.decision_log[0] == AgentDecision(
        agent="practice",
        phase=SessionPhase.GRADE,
        reason="graded paper",
        evidence_ids=[],
        ok=True,
        degraded=False,
    )


def test_build_span_tree_nests_agent_under_stage():
    session = _session()
    append_orchestration_event(
        session,
        agent="assessment",
        stage=SessionPhase.ASSESS,
        reason="paper built",
        input_payload={},
        output_payload={"items": 20},
    )
    append_orchestration_event(
        session,
        agent="practice",
        stage=SessionPhase.GRADE,
        reason="graded",
        input_payload={},
        output_payload={},
        parent_hint_stage=SessionPhase.GRADE,
    )
    tree = build_span_tree(session.event_log)
    assert tree["kind"] == "session"
    stages = {child["name"] for child in tree["children"]}
    assert "assess" in stages or SessionPhase.ASSESS.value in stages
    assert any(c["kind"] == "stage" for c in tree["children"])


def test_default_backend_is_host_state_machine():
    backend = get_default_backend()
    assert isinstance(backend, HostStateMachineBackend)
    assert backend.name == "host_state_machine"


def test_langgraph_backend_is_optional_stub():
    stub = LangGraphBackend()
    assert stub.name == "langgraph"
    try:
        stub.require_runtime()
        raised = False
    except NotImplementedError:
        raised = True
    assert raised is True
