"""P8 concept micro-lesson resource slot."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.concept_lesson import get_concept_lesson
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    SessionState,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "pilot"


def test_p8_assessment_has_one_at_a_time_class():
    text = (ROOT / "frontend/src/pages/Assessment.tsx").read_text(encoding="utf-8")
    assert "assessment-one-at-a-time" in text


def test_p8_countdown_exposes_pause_api():
    text = (ROOT / "frontend/src/hooks/useCountdown.ts").read_text(encoding="utf-8")
    assert "isPaused" in text
    assert "setIsPaused(true)" in text
    assert "if (!enabled || isPaused) return undefined" in text


def test_p8_socratic_has_concept_exit():
    text = (ROOT / "frontend/src/components/SocraticPanel.tsx").read_text(encoding="utf-8")
    assert "概念微课" in text or "concept-micro" in text
    assert "getConceptLesson" in text or "concept-lesson" in text or "script_steps" in text


def test_p8_concept_lesson_has_asset_slot():
    lesson = get_concept_lesson("mult_3digit")
    assert lesson is not None
    assert lesson.asset_url
    assert lesson.storyboard_url and lesson.storyboard_url.endswith(".md")
    assert lesson.poster_url and lesson.poster_url.endswith(".svg")
    assert lesson.media_status == "poster"
    assert lesson.video_slot_url and lesson.video_slot_url.endswith(".mp4")
    assert lesson.duration_sec >= 30
    assert lesson.script_steps
    assert lesson.no_final_answer is True


def test_p8_concept_lesson_api(tmp_path: Path):
    store = SessionStore(tmp_path)
    session = SessionState(
        session_id="c8",
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        paper=AssessmentPaper(
            items=[
                AssessmentItem(
                    id="q1",
                    stem="125×36",
                    type="fill",
                    difficulty="easy",
                    knowledge_ids=["mult_3digit"],
                )
            ],
            grade=5,
            curriculum_label="北京·人教",
        ),
    )
    store.save(session)
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/sessions/c8/items/q1/concept-lesson")
    assert r.status_code == 200
    body = r.json()["lesson"]
    assert body["asset_url"]
    assert body["script_steps"]
    assert body.get("storyboard_url")
    assert body.get("poster_url")
    assert body.get("media_status") == "poster"
    story = client.get(body["storyboard_url"])
    assert story.status_code == 200
    assert "终答" in story.text
    poster = client.get(body["poster_url"])
    assert poster.status_code == 200
    assert b"<svg" in poster.content.lower()


def test_p8_concept_manifest_exists():
    manifest = ROOT / "data/pilot/assets/concept/manifest.json"
    assert manifest.is_file()
    data = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    assert data.get("version", "").startswith("1.")
    assert len(data.get("lessons") or []) >= 5
