"""Tests for assessment timeout validation on submit."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from pathlib import Path

from ilearn.api.app import create_app
from ilearn.core.assessment_timeout import ASSESSMENT_TIMEOUT_SECONDS
from ilearn.core.schemas import SessionState

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )


def test_submit_marks_timeout_when_past_window(tmp_path: Path):
    setup = _client(tmp_path)
    sid = setup.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = setup.post(f"/sessions/{sid}/assessment").json()
    started = datetime.now(timezone.utc) - timedelta(
        seconds=ASSESSMENT_TIMEOUT_SECONDS + 60
    )
    store_path = tmp_path / f"{sid}.json"
    session = SessionState.model_validate_json(store_path.read_text(encoding="utf-8"))
    session.metadata["assessment_started_at"] = started.isoformat()
    store_path.write_text(session.model_dump_json(), encoding="utf-8")

    # Fresh client so SessionStore cache does not hold the pre-backdate session.
    client = _client(tmp_path)
    answers = {paper["items"][0]["id"]: ""}
    out = client.post(f"/sessions/{sid}/submit", json={"answers": answers}).json()
    assert out["metadata"].get("assessment_timed_out") is True


def test_assessment_started_at_set_on_adaptive_start(tmp_path: Path):
    client = _client(tmp_path)
    sid = client.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/assessment/adaptive/start")
    session = client.get(f"/sessions/{sid}").json()
    assert session["metadata"].get("assessment_started_at")


def test_effectiveness_demo_is_simulated(tmp_path: Path):
    client = _client(tmp_path)
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    metrics = client.get(f"/sessions/{sid}/effectiveness").json()["metrics"]
    assert metrics["is_simulated"] is True
    assert "演示" in metrics["data_source"]


def test_pdf_backend_endpoint(tmp_path: Path):
    client = _client(tmp_path)
    body = client.get("/system/pdf-backend").json()
    assert body["backend"] in ("weasyprint", "fpdf2")
    assert "weasyprint_available" in body
