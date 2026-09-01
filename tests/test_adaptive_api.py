"""HTTP tests for adaptive cold-start assessment endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"
BEIJING = "\u5317\u4eac"


def _client(tmp_path):
    return TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT_DATA,
            llm=None,
        )
    )


def test_adaptive_start_and_continue_keep_full_paper_at_20(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": BEIJING, "grade": 5, "age": 11}
    ).json()["session_id"]

    start = c.post(f"/sessions/{sid}/assessment/adaptive/start", json={})
    assert start.status_code == 200
    body = start.json()
    assert body["is_anchor"] is True
    assert 1 <= len(body["paper"]["items"]) <= 8
    assert body["delivered"] == len(body["paper"]["items"])

    anchor_results = [
        {
            "item_id": item["id"],
            "knowledge_ids": item.get("knowledge_ids") or [],
            "is_correct": False,
        }
        for item in body["paper"]["items"]
    ]
    cont = c.post(
        f"/sessions/{sid}/assessment/adaptive/continue",
        json={"anchor_results": anchor_results},
    )
    assert cont.status_code == 200
    full = cont.json()
    assert full["is_anchor"] is False
    assert len(full["paper"]["items"]) == 20
    assert full["delivered"] == 20

    # Default assessment path still returns 20.
    other = c.post(
        "/sessions", json={"region": BEIJING, "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = c.post(f"/sessions/{other}/assessment").json()
    assert len(paper["items"]) == 20


def test_adaptive_continue_sets_session_paper_for_submit(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": BEIJING, "grade": 5, "age": 11}
    ).json()["session_id"]
    start = c.post(f"/sessions/{sid}/assessment/adaptive/start", json={}).json()
    cont = c.post(
        f"/sessions/{sid}/assessment/adaptive/continue",
        json={
            "anchor_results": [
                {
                    "item_id": item["id"],
                    "knowledge_ids": item.get("knowledge_ids") or [],
                    "is_correct": True,
                }
                for item in start["paper"]["items"]
            ]
        },
    ).json()
    answers = {
        item["id"]: (item.get("answer_key") or "")
        for item in cont["paper"]["items"]
    }
    submit = c.post(f"/sessions/{sid}/submit", json={"answers": answers})
    assert submit.status_code == 200
    assert len(submit.json()["answers"]) == 20


def test_adaptive_anchor_allows_socratic_tutor(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": BEIJING, "grade": 5, "age": 11}
    ).json()["session_id"]

    start = c.post(f"/sessions/{sid}/assessment/adaptive/start", json={})
    assert start.status_code == 200
    item_id = start.json()["paper"]["items"][0]["id"]

    tutor = c.post(f"/sessions/{sid}/tutor", json={"item_id": item_id})
    assert tutor.status_code == 200
    assert tutor.json().get("message")


def test_replan_after_practice_loop_keeps_practice_phase(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": BEIJING, "grade": 5, "age": 11}
    ).json()["session_id"]
    start = c.post(f"/sessions/{sid}/assessment/adaptive/start", json={}).json()
    cont = c.post(
        f"/sessions/{sid}/assessment/adaptive/continue",
        json={
            "anchor_results": [
                {
                    "item_id": item["id"],
                    "knowledge_ids": item.get("knowledge_ids") or [],
                    "is_correct": False,
                }
                for item in start["paper"]["items"]
            ]
        },
    ).json()
    answers = {item["id"]: "" for item in cont["paper"]["items"]}
    c.post(f"/sessions/{sid}/submit", json={"answers": answers})
    run = c.post(f"/sessions/{sid}/run")
    assert run.status_code == 200
    assert run.json()["phase"] == "practice"
    assert run.json()["loop_count"] == 1

    replan = c.post(f"/sessions/{sid}/replan")
    assert replan.status_code == 200
    assert "markdown" in replan.json()
    phase = c.get(f"/sessions/{sid}/phase").json()
    assert phase["phase"] == "practice"
    assert phase["loop_count"] == 1
