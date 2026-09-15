from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.api.waitlist import create_waitlist_router

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


def test_healthz(tmp_path: Path):
    r = _client(tmp_path).get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "ilearn"}


def test_waitlist_requires_email(tmp_path: Path):
    r = _client(tmp_path).post("/waitlist", json={"role": "parent"})
    assert r.status_code == 422


def test_waitlist_writes_jsonl(tmp_path: Path):
    wait_path = tmp_path / "waitlist.jsonl"
    app = FastAPI()
    app.include_router(create_waitlist_router(path=wait_path))
    client = TestClient(app)
    r = client.post(
        "/waitlist",
        json={"email": "early@example.com", "role": "teacher", "note": "pilot"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    line = wait_path.read_text(encoding="utf-8").strip()
    assert "early@example.com" in line
    assert "teacher" in line
