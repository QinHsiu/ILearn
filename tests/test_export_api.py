"""API tests for PDF export endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _client(tmp_path):
    return TestClient(
        create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT_DATA, llm=None)
    )


def _graded_session(client: TestClient) -> str:
    sid = client.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11, "nickname": "导出测"}
    ).json()["session_id"]
    paper = client.post(f"/sessions/{sid}/assessment").json()
    answers = {item["id"]: (item.get("answer_key") or "") for item in paper["items"]}
    client.post(f"/sessions/{sid}/submit", json={"answers": answers})
    client.post(f"/sessions/{sid}/run")
    return sid


def test_export_assessment_pdf_returns_pdf(tmp_path):
    c = _client(tmp_path)
    sid = _graded_session(c)
    r = c.get(f"/sessions/{sid}/export/assessment.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert "attachment" in r.headers.get("content-disposition", "")


def test_export_report_pdf_returns_pdf(tmp_path):
    c = _client(tmp_path)
    sid = _graded_session(c)
    r = c.get(f"/sessions/{sid}/export/report.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_export_assessment_pdf_before_grade_returns_422(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    c.post(f"/sessions/{sid}/assessment")
    r = c.get(f"/sessions/{sid}/export/assessment.pdf")
    assert r.status_code == 422
