from pathlib import Path

from ilearn.agents.guard import SAFE_FALLBACK
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore


PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


class LeakyTutor:
    name = "tutor"

    def start(self, item, error_tag, **kwargs):
        from ilearn.core.schemas import TutorTurn

        return TutorTurn(
            phase="locate_gap",
            message=f"答案是{item.answer_key}",
            error_tag=error_tag,
        )

    def step(self, state, user_message, item, error_tag=None, **kwargs):
        from ilearn.core.schemas import TutorTurn

        return TutorTurn(
            phase="hint_1",
            message=f"填{item.answer_key}",
            error_tag=None,
        )


def test_orchestrator_replaces_leaky_tutor_start(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
        tutor=LeakyTutor(),
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    orch.grade(sid)
    item = paper.items[0]

    turn = orch.tutor_start(sid, item.id)

    assert item.answer_key not in turn.message
    assert turn.message == SAFE_FALLBACK
    session = orch._store.load(sid)
    assert any(row.agent == "guard" for row in session.decision_log)
