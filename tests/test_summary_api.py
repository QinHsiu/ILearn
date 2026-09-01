from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

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


def test_summary_teacher_and_parent(tmp_path: Path):
    client = _client(tmp_path)
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    tr = client.get(f"/sessions/{sid}/summary/teacher")
    assert tr.status_code == 200
    body = tr.json()
    assert body["student_count"] == 35
    assert "top_weaknesses" in body
    assert "narrative" in body
    pr = client.get(f"/sessions/{sid}/summary/parent")
    assert pr.status_code == 200
    assert pr.json()["child_name"] == "小明"
    assert "daily_practice_tips" in pr.json()


def test_summary_student(tmp_path: Path):
    client = _client(tmp_path)
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/summary/student")
    assert r.status_code == 200
    body = r.json()
    assert body["total_tasks"] == 5
    assert body["stars_earned"] == 5
    assert "current_task" in body


def test_summary_student_missing_404(tmp_path: Path):
    assert _client(tmp_path).get("/sessions/missing/summary/student").status_code == 404


def test_summary_missing_session_404(tmp_path: Path):
    client = _client(tmp_path)
    assert client.get("/sessions/missing/summary/teacher").status_code == 404
    assert client.get("/sessions/missing/summary/parent").status_code == 404
