from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app


PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _client(tmp_path):
    return TestClient(
        create_app(
            sessions_dir=tmp_path / "sessions",
            pilot_data_dir=PILOT_DATA,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )


def _create_session(client, nickname):
    return client.post(
        "/sessions",
        json={"region": "北京", "grade": 5, "age": 11, "nickname": nickname},
    ).json()["session_id"]


def test_dashboard_filters_parent_and_teacher_relationships(tmp_path):
    client = _client(tmp_path)
    session_id = _create_session(client, "小明")
    other_id = _create_session(client, "小红")

    assert client.post(
        "/dashboard/parent/bind",
        json={"parent_id": "p1", "session_id": session_id},
    ).status_code == 204
    assert client.post(
        "/dashboard/teacher/bind",
        json={"teacher_id": "t1", "class_id": "c1", "session_id": session_id},
    ).status_code == 204

    children = client.get("/dashboard/parent/p1/children")
    assert children.status_code == 200
    assert children.json()[0]["session_id"] == session_id
    assert client.get("/dashboard/parent/p2/children").json() == []
    assert client.get(f"/dashboard/parent/p1/child/{other_id}").status_code == 404
    mismatch = client.get(f"/dashboard/teacher/t2/student/{session_id}")
    assert mismatch.status_code == 404

    classes = client.get("/dashboard/teacher/t1/classes")
    assert classes.status_code == 200
    assert classes.json()[0]["class_id"] == "c1"
    assert client.get("/dashboard/teacher/t1/class/c1/students").status_code == 200


def test_dashboard_returns_empty_valid_lists_and_rejects_wrong_teacher(tmp_path):
    client = _client(tmp_path)
    assert client.get("/dashboard/parent/p-empty/children").json() == []
    assert client.get("/dashboard/teacher/t-empty/classes").json() == []
    assert client.get(
        "/dashboard/teacher/t-empty/class/c-empty/students"
    ).json() == []
    empty_students = client.get(
        "/dashboard/teacher/t-empty/class/c-empty/students"
    )
    assert empty_students.status_code == 200
