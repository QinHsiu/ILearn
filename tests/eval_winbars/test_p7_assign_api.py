"""P7 assign API smoke."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def test_p7_assign_endpoint(tmp_path: Path):
    store = SessionStore(tmp_path)
    session = SessionState(
        session_id="t7",
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        paper=AssessmentPaper(
            items=[
                AssessmentItem(
                    id="q1",
                    stem="题",
                    type="fill",
                    difficulty="easy",
                    knowledge_ids=["kp1"],
                )
            ],
            grade=5,
            curriculum_label="北京·人教",
        ),
        diagnosis=DiagnosisReport(
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp1",
                    knowledge_name="小数乘法",
                    score_rate=0.2,
                    level="weak",
                )
            ],
            curriculum_label="北京·人教",
        ),
    )
    store.save(session)
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.post(
        "/sessions/t7/tiers/assign",
        json={
            "students": [
                {"name": "A", "avg_mastery": 0.2},
                {"name": "B", "avg_mastery": 0.5},
                {"name": "C", "avg_mastery": 0.9},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["receipt"]["status"] == "assigned"
    assert body["item_counts"]["basic"] >= 3
    receipt = client.get("/sessions/t7/tiers/receipt")
    assert receipt.status_code == 200
    # Second assign appends timeline
    r2 = client.post("/sessions/t7/tiers/assign", json={"topic": "小数乘法"})
    assert r2.status_code == 200
    timeline = client.get("/sessions/t7/tiers/timeline")
    assert timeline.status_code == 200
    assert timeline.json()["count"] >= 2
