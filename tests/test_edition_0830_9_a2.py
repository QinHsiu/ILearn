"""Edition 0830_9 A2 — session create region gate, GET, heartbeat."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_create_rejects_unknown_region(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    r = client.post("/sessions", json={"region": "广州", "grade": 5, "age": 11})
    assert r.status_code in (400, 422)
    body = r.json()
    assert body.get("error_code") == "E-004"


def test_create_allows_shanghai_alias(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    r = client.post("/sessions", json={"region": "shanghai", "grade": 5, "age": 11})
    assert r.status_code == 200
    assert "session_id" in r.json()
    sid = r.json()["session_id"]
    g = client.get(f"/sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["profile"]["region"] == "上海"


def test_get_session_and_heartbeat(tmp_path: Path):
    client = TestClient(create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT, llm=None))
    sid = client.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    g = client.get(f"/sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["session_id"] == sid
    h = client.post(f"/sessions/{sid}/heartbeat")
    assert h.status_code == 200
    assert h.json()["ok"] is True
    assert "phase" in h.json()
    assert "server_time" in h.json()
    missing = client.get("/sessions/does-not-exist")
    assert missing.status_code == 404
    missing_hb = client.post("/sessions/does-not-exist/heartbeat")
    assert missing_hb.status_code == 404
