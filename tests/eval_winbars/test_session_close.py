"""W6: session-close ritual — evidence-first today/tomorrow, no final answers."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    KnowledgeEvidence,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)
from ilearn.core.session_close import build_session_close, stamp_session_close
from ilearn.storage.sessions import SessionStore

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "pilot"


def _session(*, closed: bool = False) -> SessionState:
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="q1",
                stem="1.2×3=?",
                type="fill",
                difficulty="easy",
                knowledge_ids=["dec_mult"],
                answer_key="3.6",
            )
        ],
        grade=5,
        curriculum_label="北京·人教",
    )
    meta: dict = {}
    if closed:
        meta["session_closed_at"] = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc).isoformat()
    return SessionState(
        session_id="sc1",
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        paper=paper,
        grades=[GradeResult(item_id="q1", final_correct=False)],
        evidence_log=[
            KnowledgeEvidence(
                session_id="sc1",
                item_id="q1",
                knowledge_id="dec_mult",
                lane="probe",
                correct=False,
            )
        ],
        diagnosis=DiagnosisReport(
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="dec_mult",
                    knowledge_name="小数乘法",
                    score_rate=0.3,
                    level="weak",
                )
            ],
            curriculum_label="北京·人教",
        ),
        metadata=meta,
    )


def test_session_close_is_open_until_stamped_and_never_leaks_answer():
    view = build_session_close(_session())
    assert view.closed is False
    assert view.next_challenge == "小数乘法"
    assert "证据" in view.headline
    assert "终答" in view.honesty_note or "不" in view.honesty_note
    dumped = view.model_dump()
    assert "3.6" not in str(dumped)
    assert "最终答案" not in str(dumped)


def test_stamp_session_close_marks_closed_and_writes_parent_line():
    session = _session()
    stamp_session_close(session)
    view = build_session_close(session)
    assert view.closed is True
    assert view.closed_at
    assert "收工" in view.parent_line
    assert "小数乘法" in view.parent_line
    assert "3.6" not in view.parent_line


def test_session_close_api_round_trip(tmp_path: Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    store = SessionStore(sessions_dir)
    session = _session()
    store.save(session)
    client = TestClient(
        create_app(
            sessions_dir=sessions_dir,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    opened = client.get("/sessions/sc1/session-close")
    assert opened.status_code == 200
    assert opened.json()["closed"] is False
    stamped = client.post("/sessions/sc1/session-close")
    assert stamped.status_code == 200
    body = stamped.json()
    assert body["closed"] is True
    assert "收工" in body["parent_line"]
    assert "3.6" not in stamped.text
    again = client.get("/sessions/sc1/session-close")
    assert again.json()["closed"] is True
