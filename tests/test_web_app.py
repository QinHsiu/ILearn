import importlib.util

import httpx
import pytest


def test_web_app_module_exists():
    assert importlib.util.find_spec("ilearn.web.app") is not None


def test_api_client_runs_assessment_flow_over_http():
    from ilearn.web.app import ILearnAPI

    requests = []

    def handler(request):
        requests.append((request.method, request.url.path))
        if request.url.path == "/sessions":
            assert request.read() == b'{"region":"Beijing","grade":5,"age":11}'
            return httpx.Response(200, json={"session_id": "session-1"})
        if request.url.path.endswith("/assessment"):
            return httpx.Response(200, json={"items": [{"id": "q1"}]})
        if request.url.path.endswith("/submit"):
            assert request.read() == b'{"answers":{"q1":"12"}}'
            return httpx.Response(200, json={"session_id": "session-1"})
        if request.url.path.endswith("/run"):
            return httpx.Response(200, json={"grades": [{"final_correct": True}]})
        return httpx.Response(
            200,
            json={"markdown": "# Report", "session": {"session_id": "session-1"}},
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    api = ILearnAPI("http://api.test/", client=http)

    session_id, paper = api.start_session("Beijing", 5, 11)
    state = api.submit_and_run(session_id, {"q1": "12"})
    report = api.get_report(session_id)

    assert paper["items"][0]["id"] == "q1"
    assert state["grades"][0]["final_correct"] is True
    assert report["markdown"] == "# Report"
    assert requests == [
        ("POST", "/sessions"),
        ("POST", "/sessions/session-1/assessment"),
        ("POST", "/sessions/session-1/submit"),
        ("POST", "/sessions/session-1/run"),
        ("GET", "/sessions/session-1/report"),
    ]


def test_api_client_surfaces_server_error_detail():
    from ilearn.web.app import ILearnAPI

    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400, json={"detail": "invalid profile"})
        )
    )

    with pytest.raises(RuntimeError, match="invalid profile"):
        ILearnAPI("http://api.test", client=http).start_session("x", 5, 11)


def test_report_helpers_prepare_readable_summary():
    from ilearn.web.app import (
        ability_label,
        ability_progress,
        grade_summary,
        mastery_rows,
    )

    grades = [
        {"final_correct": True},
        {"final_correct": False, "grading_degraded": True},
    ]
    mastery = [
        {
            "knowledge_id": "fraction",
            "knowledge_name": "分数加法",
            "score_rate": 0.75,
            "level": "unstable",
            "error_tag_counts": {"calc_error": 2},
        }
    ]

    assert grade_summary(grades) == {"correct": 1, "total": 2, "degraded": 1}
    assert mastery_rows(mastery) == [
        {
            "知识点": "分数加法",
            "掌握率": "75%",
            "水平": "需巩固",
            "主要错因": "计算错误 × 2",
        }
    ]
    assert ability_label("mental_math") == "心算能力"
    assert ability_progress(75) == 0.75
    assert ability_progress(-10) == 0.0
    assert ability_progress(120) == 1.0
