from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app


PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ILEARN_PARENT_USERNAME", "parent-demo")
    monkeypatch.setenv("ILEARN_PARENT_PASSWORD", "parent-secret")
    monkeypatch.setenv("ILEARN_PARENT_USER_ID", "parent-1")
    monkeypatch.setenv("ILEARN_TEACHER_USERNAME", "teacher-demo")
    monkeypatch.setenv("ILEARN_TEACHER_PASSWORD", "teacher-secret")
    monkeypatch.setenv("ILEARN_TEACHER_USER_ID", "teacher-1")
    return TestClient(
        create_app(
            sessions_dir=tmp_path / "sessions",
            pilot_data_dir=PILOT_DATA,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )


def test_login_accepts_parent_and_teacher_credentials(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    parent = client.post(
        "/auth/login",
        json={
            "role": "parent",
            "username": "parent-demo",
            "password": "parent-secret",
        },
    )
    teacher = client.post(
        "/auth/login",
        json={
            "role": "teacher",
            "username": "teacher-demo",
            "password": "teacher-secret",
        },
    )

    assert parent.status_code == 200
    assert parent.json() == {"role": "parent", "user_id": "parent-1"}
    assert teacher.status_code == 200
    assert teacher.json() == {"role": "teacher", "user_id": "teacher-1"}


def test_login_rejects_invalid_password_with_generic_401(tmp_path, monkeypatch):
    response = _client(tmp_path, monkeypatch).post(
        "/auth/login",
        json={"role": "parent", "username": "parent-demo", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid credentials"


def test_login_rejects_invalid_role_with_400(tmp_path, monkeypatch):
    response = _client(tmp_path, monkeypatch).post(
        "/auth/login",
        json={"role": "student", "username": "demo", "password": "demo"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid role"


def test_create_app_registers_auth_route(tmp_path, monkeypatch):
    response = _client(tmp_path, monkeypatch).post(
        "/auth/login",
        json={
            "role": "parent",
            "username": "parent-demo",
            "password": "parent-secret",
        },
    )

    assert response.status_code == 200
