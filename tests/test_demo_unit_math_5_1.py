from pathlib import Path
from fastapi.testclient import TestClient
from ilearn.api.app import create_app
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit
from ilearn.core.schemas import SessionPhase

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_load_and_seed_math_5_1():
    unit = load_demo_unit("math_5_1")
    assert unit["id"] == "math_5_1"
    session = seed_demo_session(unit)
    assert session.phase == SessionPhase.PLAN
    assert session.paper is not None and len(session.paper.items) == 20
    assert session.grades and len(session.grades) == 20
    assert session.diagnosis is not None
    assert session.plan is not None
    assert session.metadata.get("demo_unit") == "math_5_1"
    assert "demo_class_data" in session.metadata
    assert len(session.evidence_log) >= 5


def test_demo_session_api(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
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
    assert g.json()["metadata"]["demo_unit"] == "math_5_1"
    bad = client.post("/demo/units/nope/session")
    assert bad.status_code == 404
