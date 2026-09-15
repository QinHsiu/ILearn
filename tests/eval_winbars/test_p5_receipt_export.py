"""P5 grading receipts exposure + PDF export win-bar tests."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    GradingReceipt,
    SessionState,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def _seed(store: SessionStore) -> None:
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="小明")
    session = SessionState(
        session_id="recv1",
        profile=profile,
        paper=AssessmentPaper(
            items=[
                AssessmentItem(
                    id="q1",
                    stem="1+1",
                    type="fill",
                    difficulty="easy",
                    knowledge_ids=["kp1"],
                    answer_key="2",
                )
            ],
            grade=5,
            curriculum_label="北京·人教",
        ),
        grades=[
            GradeResult(
                item_id="q1",
                final_correct=True,
                receipt=GradingReceipt(
                    paper_created_at=datetime.now(timezone.utc),
                    grader_version="1.0.0",
                    model_id=None,
                ),
            )
        ],
    )
    store.save(session)


def test_p5_grading_receipts_endpoint(tmp_path: Path):
    store = SessionStore(tmp_path)
    _seed(store)

    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/sessions/recv1/grading-receipts")
    assert r.status_code == 200
    body = r.json()
    assert len(body["receipts"]) == 1
    assert body["receipts"][0]["receipt"]["grader_version"] == "1.0.0"
    assert body["receipts"][0]["item_id"] == "q1"


def test_p5_grading_receipts_pdf(tmp_path: Path):
    store = SessionStore(tmp_path)
    _seed(store)
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/sessions/recv1/export/grading-receipts.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
