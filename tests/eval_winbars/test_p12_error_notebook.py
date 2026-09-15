"""P12 error notebook without answer leak + repractice + PDF."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.error_notebook import build_error_notebook
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    ItemSourceRef,
    SessionState,
    StudentAnswer,
    StudentProfile,
)
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def _session() -> SessionState:
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="小明")
    item = AssessmentItem(
        id="q1",
        stem="1.2×3=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["kp1"],
        answer_key="3.6",
        rubric_steps=["对齐", "相乘", "点小数点"],
        source_refs=[ItemSourceRef(example_id="ex1", source_label="试点")],
    )
    return SessionState(
        session_id="s1",
        profile=profile,
        paper=AssessmentPaper(items=[item], grade=5, curriculum_label="北京·人教"),
        answers=[StudentAnswer(item_id="q1", answer_text="3")],
        grades=[GradeResult(item_id="q1", final_correct=False)],
    )


def test_p12_notebook_hides_answer_key():
    notebook = build_error_notebook(_session())
    assert len(notebook) == 1
    assert notebook[0]["answer_key"] is None
    assert "3.6" not in str(notebook[0])
    assert notebook[0]["rubric_steps"]
    assert notebook[0]["citation_label"] == "试点"


def test_p12_repractice_and_pdf(tmp_path: Path):
    store = SessionStore(tmp_path)
    session = _session()
    session.session_id = "s12"
    store.save(session)
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.post("/sessions/s12/error-notebook/repractice")
    assert r.status_code == 200
    body = r.json()
    assert body["item_count"] >= 1
    assert all(it.get("answer_key") is None for it in body["paper"]["items"])
    pdf = client.get("/sessions/s12/export/error-notebook.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_w4_error_notebook_api_has_block_summary_and_masks_final_answer(tmp_path: Path):
    """W4: notebook block payload — count, knowledge focus, mask note; 3.6 never leaks."""
    store = SessionStore(tmp_path)
    session = _session()
    session.session_id = "s13"
    store.save(session)
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/sessions/s13/error-notebook")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["knowledge_focus"] == ["kp1"]
    assert "终答" in body["mask_note"]
    assert body["repractice_ready"] is True
    assert body["items"][0]["answer_key"] is None
    assert body["items"][0]["student_answer"] == "3"
    assert "3.6" not in r.text
