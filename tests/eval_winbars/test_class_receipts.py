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


def test_class_timeline_completion_follows_repractice(tmp_path: Path):
    """W2: assign → not_started; activate repractice → in_repractice; submit → submitted."""
    store = SessionStore(tmp_path)
    rel_path = tmp_path / "relationships.json"
    relationships = RelationshipStore(rel_path, store)
    store.save(
        SessionState(
            session_id="s-a",
            profile=StudentProfile(region="北京", grade=5, age=11, nickname="甲"),
        )
    )
    relationships.bind_teacher("t1", "c1", "s-a")
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=rel_path,
            llm=None,
        )
    )
    url = "/dashboard/teacher/t1/class/c1/assignment-timeline"

    r = client.post(
        "/dashboard/teacher/t1/class/c1/tiers/assign-batch",
        json={"session_ids": ["s-a"], "topic": "小数乘法"},
    )
    assert r.status_code == 200
    row = client.get(url).json()["timeline"][0]
    assert row["completion"]["state"] == "not_started"
    assert row["completion"]["label"] == "未开始"

    r = client.post("/sessions/s-a/repractice/activate")
    assert r.status_code == 200
    row = client.get(url).json()["timeline"][0]
    assert row["completion"]["state"] == "in_repractice"
    assert row["completion"]["label"] == "重练中"

    item_ids = [item["id"] for item in r.json()["paper"]["items"]]
    r = client.post(
        "/sessions/s-a/submit",
        json={"answers": {iid: "分步：先对齐再相乘" for iid in item_ids}},
    )
    assert r.status_code == 200, r.text
    row = client.get(url).json()["timeline"][0]
    assert row["completion"]["state"] == "submitted"
    assert row["completion"]["label"] == "已提交"
    assert row["completion"]["at"]

    summary = client.get(url).json()["completion_summary"]
    assert summary == {"not_started": 0, "in_repractice": 0, "submitted": 1}
