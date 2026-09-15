"""P10 decision-log summary for trust win-bar."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def test_p10_decision_log_summary_on_demo(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/decision-log/summary")
    assert r.status_code == 200
    body = r.json()
    assert "phases" in body
    assert "agents" in body
    assert isinstance(body["phases"], list)
