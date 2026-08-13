from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _client(tmp_path):
    return TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT_DATA,
            llm=None,
        )
    )


def test_session_assessment_flow(tmp_path):
    c = _client(tmp_path)
    r = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    assert len(paper["items"]) == 20


def test_full_session_api_flow(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    answers = {item["id"]: (item.get("answer_key") or "") for item in paper["items"]}

    submit = c.post(f"/sessions/{sid}/submit", json={"answers": answers})
    assert submit.status_code == 200

    run = c.post(f"/sessions/{sid}/run")
    assert run.status_code == 200
    state = run.json()
    assert len(state["grades"]) == 20
    assert state["diagnosis"] is not None
    assert state["plan"] is not None

    report = c.get(f"/sessions/{sid}/report")
    assert report.status_code == 200
    body = report.json()
    assert "markdown" in body
    assert "session" in body
    assert "计划" in body["markdown"] or "学习计划" in body["markdown"]


def test_submit_persists_optional_item_meta(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    item_id = paper["items"][0]["id"]

    response = c.post(
        f"/sessions/{sid}/submit",
        json={
            "answers": {item_id: ""},
            "item_meta": {item_id: {"skipped": True, "elapsed_ms": 1200}},
        },
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["item_meta"] == {
        item_id: {"skipped": True, "elapsed_ms": 1200}
    }


def test_stepwise_endpoints(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    answers = {item["id"]: (item.get("answer_key") or "") for item in paper["items"]}
    c.post(f"/sessions/{sid}/submit", json={"answers": answers})

    grades = c.post(f"/sessions/{sid}/grade").json()
    assert len(grades) == 20

    diagnosis = c.post(f"/sessions/{sid}/diagnose").json()
    assert "knowledge_mastery" in diagnosis

    plan = c.post(f"/sessions/{sid}/plan").json()
    assert "markdown" in plan


def test_missing_session_returns_404(tmp_path):
    c = _client(tmp_path)
    r = c.post("/sessions/nope/assessment")
    assert r.status_code == 404


def test_phase_endpoint(tmp_path):
    c = _client(tmp_path)
    sid = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11}).json()[
        "session_id"
    ]
    c.post(f"/sessions/{sid}/assessment")
    phase = c.get(f"/sessions/{sid}/phase").json()
    assert phase["phase"] == "practice"
    assert phase["loop_count"] == 0


def test_submit_images_accepts_base64(tmp_path):
    c = _client(tmp_path)
    sid = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11}).json()[
        "session_id"
    ]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    item_id = paper["items"][0]["id"]
    r = c.post(
        f"/sessions/{sid}/submit-images",
        json={
            "images": [
                {
                    "item_id": item_id,
                    "image_base64": "aGVsbG8=",
                    "mime_type": "image/png",
                }
            ]
        },
    )
    assert r.status_code == 200
    state = r.json()
    assert len(state["image_answers"]) == 1
    assert state["image_answers"][0]["item_id"] == item_id


def test_followup_endpoint(tmp_path):
    c = _client(tmp_path)
    sid = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11}).json()[
        "session_id"
    ]
    paper = c.post(f"/sessions/{sid}/assessment").json()
    answers = {item["id"]: "wrong" for item in paper["items"]}
    c.post(f"/sessions/{sid}/submit", json={"answers": answers})
    c.post(f"/sessions/{sid}/grade")
    c.post(f"/sessions/{sid}/diagnose")
    c.post(f"/sessions/{sid}/plan")

    r = c.post(f"/sessions/{sid}/followup")
    assert r.status_code == 200
    followup_paper = r.json()
    assert 1 <= len(followup_paper["items"]) <= 10

    phase = c.get(f"/sessions/{sid}/phase").json()
    assert phase["phase"] == "practice"
    assert phase["loop_count"] == 1


def test_cors_allows_vite_origin(tmp_path):
    c = _client(tmp_path)
    r = c.options(
        "/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allows_legacy_streamlit_origin(tmp_path):
    c = _client(tmp_path)
    r = c.options(
        "/sessions",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8501"


@patch("ilearn.api.app.Orchestrator")
@patch("ilearn.api.app.LLMClient.from_env")
@patch("ilearn.api.app.load_dotenv")
def test_create_app_loads_dotenv_and_wires_available_llm(
    mock_load_dotenv,
    mock_from_env,
    mock_orchestrator,
    tmp_path,
):
    llm = MagicMock()
    llm.available.return_value = True
    mock_from_env.return_value = llm

    create_app(sessions_dir=tmp_path, pilot_data_dir=PILOT_DATA)

    mock_load_dotenv.assert_called_once()
    assert mock_orchestrator.call_args.kwargs["llm"] is llm


def test_list_sessions_by_nickname(tmp_path):
    c = _client(tmp_path)
    sid = c.post(
        "/sessions",
        json={"region": "北京", "grade": 5, "age": 11, "nickname": "小明"},
    ).json()["session_id"]
    listed = c.get("/sessions", params={"nickname": "小明"}).json()
    assert listed == [
        {
            "session_id": sid,
            "nickname": "小明",
            "grade": 5,
            "phase": "onboard",
        }
    ]


def test_list_sessions_requires_nickname(tmp_path):
    c = _client(tmp_path)
    assert c.get("/sessions").status_code == 400


def test_delete_session(tmp_path):
    c = _client(tmp_path)
    sid = c.post("/sessions", json={"region": "北京", "grade": 5, "age": 11}).json()[
        "session_id"
    ]
    assert c.delete(f"/sessions/{sid}").status_code == 204
    assert c.get(f"/sessions/{sid}/phase").status_code == 404
