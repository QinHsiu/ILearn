from pathlib import Path

from ilearn.core.orchestrator import Orchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT_DATA = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_session_store_persists_state_as_json(tmp_path):
    store = SessionStore(tmp_path)
    profile = StudentProfile(region="北京", grade=5, age=11)

    created = store.create(profile)
    loaded = store.load(created.session_id)

    assert loaded == created
    assert list(tmp_path.glob("*.json")) == [tmp_path / f"{created.session_id}.json"]


def test_full_pipeline_offline(tmp_path):
    curriculum = PilotBeijingRenjiaoProvider(PILOT_DATA)
    orchestrator = Orchestrator(
        store=SessionStore(tmp_path),
        curriculum=curriculum,
        llm=None,
    )
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )

    paper = orchestrator.generate_assessment(session_id)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orchestrator.submit(session_id, answers)
    completed = orchestrator.run_after_submit(session_id)
    markdown = orchestrator.report(session_id)

    assert len(completed.grades) == 20
    assert completed.diagnosis is not None
    assert completed.plan is not None
    assert "计划" in markdown or "学习计划" in markdown
    assert SessionStore(tmp_path).load(session_id) == completed
