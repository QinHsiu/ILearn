from pathlib import Path

import pytest

from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _orchestrator(tmp_path) -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )


def test_beijing_g5_keyword_curriculum_path(tmp_path):
    orch = _orchestrator(tmp_path)
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    session = orch._store.load(sid)
    assert len(paper.items) == 20
    assert session.curriculum_citations
    assert all(c.source_label for c in session.curriculum_citations)


def test_shanghai_g5_curriculum_retrieve():
    agent = CurriculumAgent(pilot_dir=PILOT)
    ctx = AgentContext(
        session_id="sh1",
        phase=SessionPhase.ONBOARD,
        profile=StudentProfile(region="上海", grade=5, age=11),
        metadata={"curriculum_query": "分数"},
    )
    result = agent.run(ctx)
    citations = result.payload["citations"]
    assert citations
    assert any(
        "上海" in (c.source_label or "") or "sh-" in (c.source_id or "")
        for c in citations
    )


def test_curriculum_agent_hash_vector_backend(monkeypatch):
    monkeypatch.setenv("ILEARN_RETRIEVER_BACKEND", "hash_vector")
    agent = CurriculumAgent(pilot_dir=PILOT)
    ctx = AgentContext(
        session_id="hv1",
        phase=SessionPhase.ONBOARD,
        profile=StudentProfile(region="北京", grade=5, age=11),
        metadata={"curriculum_query": "同分母分数"},
    )
    result = agent.run(ctx)
    citations = result.payload["citations"]
    assert citations
    assert citations[0].source_id
    assert agent._backend == "hash_vector"


def test_curriculum_agent_defaults_to_keyword_backend(monkeypatch):
    monkeypatch.delenv("ILEARN_RETRIEVER_BACKEND", raising=False)
    agent = CurriculumAgent(pilot_dir=PILOT)
    ctx = AgentContext(
        session_id="kw1",
        phase=SessionPhase.ONBOARD,
        profile=StudentProfile(region="北京", grade=5, age=11),
        metadata={"curriculum_query": "分数加减"},
    )
    result = agent.run(ctx)
    assert result.payload["citations"]
    assert agent._backend == "keyword"
