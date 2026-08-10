from pathlib import Path

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import PendingQuestion, SessionPhase, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> tuple[MultiAgentOrchestrator, SessionStore]:
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    return orchestrator, store


def test_generate_assessment_overwrites_pending_questions_from_paper(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    session = store.load(session_id)
    session.pending_questions = [
        PendingQuestion(
            question_id="stale-question",
            expected_answer="stale-answer",
            paper_id="stale-paper",
        )
    ]
    store.save(session)

    paper = orchestrator.generate_assessment(session_id)

    pending = store.load(session_id).pending_questions
    assert [question.question_id for question in pending] == [
        item.id for item in paper.items
    ]
    assert [question.expected_answer for question in pending] == [
        item.answer_key or "" for item in paper.items
    ]
    assert {question.paper_id for question in pending} == {session_id}


def test_submit_rejects_answer_id_not_in_pending_questions(tmp_path):
    orchestrator, _ = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    orchestrator.generate_assessment(session_id)

    with pytest.raises(
        ValueError, match="answers contain unknown item ids: unknown-question"
    ):
        orchestrator.submit(session_id, {"unknown-question": "42"})


def test_submit_without_pending_questions_keeps_legacy_behavior(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    orchestrator.generate_assessment(session_id)
    session = store.load(session_id)
    session.pending_questions = []
    store.save(session)

    saved = orchestrator.submit(session_id, {"unknown-question": "42"})

    assert saved.phase == SessionPhase.GRADE


def test_submit_accepts_answer_ids_in_pending_questions(tmp_path):
    orchestrator, store = _orchestrator(tmp_path)
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    paper = orchestrator.generate_assessment(session_id)
    first_item = paper.items[0]

    saved = orchestrator.submit(
        session_id,
        {first_item.id: first_item.answer_key or ""},
    )

    assert saved.phase == SessionPhase.GRADE
    assert saved == store.load(session_id)
