from ilearn.core.effectiveness import compute_metrics, TeachingEffectivenessMetrics
from ilearn.demo.units import load_demo_unit
from ilearn.demo.seed import seed_demo_session
from fastapi.testclient import TestClient
from ilearn.api.app import create_app
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_compute_metrics_on_demo_seed():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    m = compute_metrics(session)
    assert isinstance(m, TeachingEffectivenessMetrics)
    assert m.total_questions == 20
    assert 0 <= m.pre_assessment_score <= 100
    assert m.completion_rate == 100.0
    assert m.evidence_count >= 5
    assert m.time_saved_percent > 0


def test_compute_metrics_formulas_on_demo_seed():
    session = seed_demo_session(load_demo_unit("math_5_1"))
    m = compute_metrics(session)
    assert m.pre_assessment_score == 60.0
    assert m.post_assessment_score is None
    assert m.mastery_gain == 18.0
    assert m.weakness_remaining_count == 2
    assert m.weakness_resolved_count == 1
    assert m.manual_review_count == 6
    assert m.auto_graded_count == 14
    assert m.traditional_grading_time_minutes == 40.0
    assert m.estimated_grading_time_minutes == 6.5
    assert m.time_saved_percent == 83.75
    assert m.diagnosis_confidence == 0.82
    assert m.hint_used_count == 0
    assert m.session_duration_seconds == 1680
    assert m.parent_view_count == 3
    assert m.teacher_notes_count == 2


def test_effectiveness_endpoint(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    sid = client.post("/demo/units/math_5_1/session").json()["session_id"]
    r = client.get(f"/sessions/{sid}/effectiveness")
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body and "comparison" in body
    assert "traditional_vs_ilearn" in body["comparison"]
    vs = body["comparison"]["traditional_vs_ilearn"]
    assert "grading_time" in vs
    assert "personalized" in vs
    assert "feedback_delay" in vs


def test_effectiveness_missing_session(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/sessions/missing/effectiveness")
    assert r.status_code == 404
