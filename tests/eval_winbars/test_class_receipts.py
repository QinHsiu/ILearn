"""Class-level assignment receipt aggregation (cross-session)."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.schemas import SessionState, StudentProfile
from ilearn.storage.relationships import RelationshipStore
from ilearn.storage.sessions import SessionStore

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "pilot"


def test_class_assignment_timeline_aggregates_sessions(tmp_path: Path):
    store = SessionStore(tmp_path)
    rel_path = tmp_path / "relationships.json"
    relationships = RelationshipStore(rel_path, store)

    for sid, name, stamp in (
        ("s-a", "甲", "2026-09-15T08:00:00+00:00"),
        ("s-b", "乙", "2026-09-15T09:00:00+00:00"),
    ):
        session = SessionState(
            session_id=sid,
            profile=StudentProfile(region="北京", grade=5, age=11, nickname=name),
            metadata={
                "tier_assignment_timeline": [
                    {
                        "assigned_at": stamp,
                        "topic": "小数乘法巩固",
                        "item_counts": {"basic": 2, "advanced": 1},
                    }
                ]
            },
        )
        store.save(session)
        relationships.bind_teacher("t1", "c1", sid)

    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=rel_path,
            llm=None,
        )
    )
    r = client.get("/dashboard/teacher/t1/class/c1/assignment-timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["session_count"] == 2
    assert body["timeline"][0]["student_name"] == "乙"
    assert body["timeline"][0]["item_counts"]["basic"] == 2


def test_class_batch_assign_creates_receipts(tmp_path: Path):
    store = SessionStore(tmp_path)
    rel_path = tmp_path / "relationships.json"
    relationships = RelationshipStore(rel_path, store)
    for sid, name in (("s-a", "甲"), ("s-b", "乙")):
        store.save(
            SessionState(
                session_id=sid,
                profile=StudentProfile(region="北京", grade=5, age=11, nickname=name),
            )
        )
        relationships.bind_teacher("t1", "c1", sid)

    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=rel_path,
            llm=None,
        )
    )
    r = client.post(
        "/dashboard/teacher/t1/class/c1/tiers/assign-batch",
        json={"session_ids": ["s-a", "s-b"], "topic": "小数乘法"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["assigned_count"] == 2
    assert "2 人" in body["summary"]
    timeline = client.get("/dashboard/teacher/t1/class/c1/assignment-timeline").json()
    assert timeline["count"] >= 2
