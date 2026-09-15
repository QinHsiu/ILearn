"""P6 parent actions must bind weak knowledge points + PDF card."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.parent_action_summary import build_parent_action_summary
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def test_p6_actions_mention_weak_skills():
    summary = build_parent_action_summary(
        child_name="小红",
        current_mastery=0.5,
        mastery_change=0.05,
        weak_skills=["小数意义", "小数加减"],
    )
    blob = " ".join(summary.actions + summary.focus)
    assert "小数意义" in blob
    assert len(summary.actions) >= 2


def test_p6_parent_card_pdf(tmp_path: Path):
    store = SessionStore(tmp_path)
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="小红")
    session = SessionState(
        session_id="p6",
        profile=profile,
        paper=AssessmentPaper(
            items=[
                AssessmentItem(
                    id="q1",
                    stem="题",
                    type="fill",
                    difficulty="easy",
                    knowledge_ids=["kp1"],
                )
            ],
            grade=5,
            curriculum_label="北京·人教",
        ),
        diagnosis=DiagnosisReport(
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp1",
                    knowledge_name="小数意义",
                    score_rate=0.3,
                    level="weak",
                )
            ],
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
    r = client.get("/sessions/p6/export/parent-card.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
