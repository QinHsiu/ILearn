from pathlib import Path

import pytest

from ilearn.agents.capabilities import assert_writes_allowed
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.protocol import AgentResult
from ilearn.core.schemas import (
    AssessmentPaper,
    SessionPhase,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_assessment_cannot_write_portrait():
    with pytest.raises(
        PermissionError,
        match=r"assessment cannot write \['portrait'\]",
    ):
        assert_writes_allowed("assessment", {"portrait"})


def test_diagnosis_can_write_portrait():
    assert_writes_allowed("diagnosis", {"portrait"})


class _MisassignedDiagnosisAgent:
    name = "diagnosis"

    def run(self, _ctx):
        return AgentResult(
            phase=SessionPhase.PRACTICE,
            payload={
                "paper": AssessmentPaper(
                    items=[],
                    grade=5,
                    curriculum_label="test",
                ),
            },
        )


def test_orchestrator_rejects_disallowed_known_write_before_applying(tmp_path):
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    orchestrator._assessment = _MisassignedDiagnosisAgent()

    with pytest.raises(
        PermissionError,
        match=r"diagnosis cannot write \['paper'\]",
    ):
        orchestrator.generate_assessment(session_id)

    session = store.load(session_id)
    assert session.paper is None
    assert session.portrait is None
