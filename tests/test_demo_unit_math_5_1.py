from pathlib import Path
from fastapi.testclient import TestClient
from ilearn.api.app import create_app
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit
from ilearn.core.schemas import SessionPhase

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
_CLASS_DATA_KEYS = {
    "class_size",
    "avg_mastery",
    "mastery_distribution",
    "common_weaknesses",
}


def test_load_and_seed_math_5_1():
    unit = load_demo_unit("math_5_1")
    assert unit["id"] == "math_5_1"
    session = seed_demo_session(unit)
    assert session.phase == SessionPhase.PLAN
    assert session.profile.region == "北京" and session.profile.grade == 5
    assert session.paper is not None
    assert len(session.paper.items) == 20
    assert [item.id for item in session.paper.items] == [
        f"demo_m51_{i:02d}" for i in range(1, 21)
    ]
    assert session.grades is not None
    assert len(session.grades) == 20
    assert session.diagnosis is not None
    assert session.diagnosis.knowledge_mastery
    assert session.plan is not None
    assert session.plan.markdown
    assert session.metadata.get("demo_unit") == "math_5_1"
    class_data = session.metadata.get("demo_class_data")
    assert isinstance(class_data, dict)
    assert _CLASS_DATA_KEYS <= set(class_data)
    enrichment = session.metadata.get("diagnosis_enrichment")
    assert isinstance(enrichment, dict)
    assert enrichment.get("parent_summary")
    assert enrichment.get("teacher_summary")
    assert len(session.evidence_log) >= 5


def test_demo_session_api(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path / "sessions",
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.post("/demo/units/math_5_1/session")
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert body["unit_name"]
    assert "teacher" in body["links"] and "parent" in body["links"]
    g = client.get(f"/sessions/{sid}")
    assert g.status_code == 200
    loaded = g.json()
    assert loaded["metadata"]["demo_unit"] == "math_5_1"
    assert loaded["diagnosis"] is not None
    assert len(loaded["grades"]) == 20
    assert _CLASS_DATA_KEYS <= set(loaded["metadata"]["demo_class_data"])

    children = client.get("/dashboard/parent/demo_parent/children")
    assert children.status_code == 200
    assert sid in [row["session_id"] for row in children.json()]

    students = client.get(
        "/dashboard/teacher/demo_teacher/class/demo_class_5a/students"
    )
    assert students.status_code == 200
    assert sid in [row["session_id"] for row in students.json()]

    bad = client.post("/demo/units/nope/session")
    assert bad.status_code == 404
