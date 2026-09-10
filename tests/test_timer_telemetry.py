"""Backend merge for timer_events + POST /timer-telemetry."""

from __future__ import annotations

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


def _create_assessed_session(client: TestClient) -> tuple[str, dict]:
    sid = client.post(
        "/sessions", json={"region": "北京", "grade": 5, "age": 11}
    ).json()["session_id"]
    paper = client.post(f"/sessions/{sid}/assessment").json()
    return sid, paper


def test_timer_telemetry_appends_fifo(tmp_path: Path):
    client = _client(tmp_path)
    sid, _paper = _create_assessed_session(client)
    phase_before = client.get(f"/sessions/{sid}").json()["phase"]

    first = [
        {"type": "ui_deadline", "ts": 1},
        {"type": "timer_refresh", "ts": 2},
        {"type": "item_time_flush", "ts": 3, "item_id": "q1", "thinking_ms": 10, "pause_ms": 0},
    ]
    r1 = client.post(
        f"/sessions/{sid}/timer-telemetry",
        json={"timer_events": first},
    )
    assert r1.status_code == 204

    session = client.get(f"/sessions/{sid}").json()
    assert len(session["metadata"]["timer_events"]) == 3
    assert session["phase"] == phase_before

    more = [{"type": "timer_refresh", "ts": 100 + i} for i in range(200)]
    r2 = client.post(
        f"/sessions/{sid}/timer-telemetry",
        json={"timer_events": more},
    )
    assert r2.status_code == 204

    session = client.get(f"/sessions/{sid}").json()
    events = session["metadata"]["timer_events"]
    assert len(events) == 200
    # 203 total → FIFO drop first 3 (ts 1,2,3); keep ts 100..299
    assert events[0]["ts"] == 100
    assert events[-1]["ts"] == 299
    assert session["phase"] == phase_before


def test_submit_merges_timer_events(tmp_path: Path):
    client = _client(tmp_path)
    sid, paper = _create_assessed_session(client)
    answers = {item["id"]: (item.get("answer_key") or "") for item in paper["items"]}
    events = [
        {"type": "ui_deadline", "ts": 42},
        {
            "type": "item_time_flush",
            "ts": 43,
            "item_id": paper["items"][0]["id"],
            "thinking_ms": 100,
            "pause_ms": 0,
        },
    ]
    out = client.post(
        f"/sessions/{sid}/submit",
        json={"answers": answers, "timer_events": events},
    )
    assert out.status_code == 200
    stored = out.json()["metadata"]["timer_events"]
    assert len(stored) == 2
    assert stored[0]["type"] == "ui_deadline"
    assert stored[1]["thinking_ms"] == 100


def test_timer_telemetry_patches_incomplete_meta(tmp_path: Path):
    client = _client(tmp_path)
    sid, paper = _create_assessed_session(client)
    item_id = paper["items"][0]["id"]
    phase_before = client.get(f"/sessions/{sid}").json()["phase"]

    r = client.post(
        f"/sessions/{sid}/timer-telemetry",
        json={
            "item_meta_patch": {
                item_id: {"thinking_ms_incomplete": True},
            }
        },
    )
    assert r.status_code == 204

    session = client.get(f"/sessions/{sid}").json()
    assert session["metadata"]["item_meta"][item_id]["thinking_ms_incomplete"] is True
    assert session["phase"] == phase_before
