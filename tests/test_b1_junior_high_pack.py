"""B1 junior-high pack stretch — Companion Answer citations for grade 7."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.companion import CompanionAgent
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.providers.retriever import load_curriculum_sources


def test_load_curriculum_sources_includes_b1_pack():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    sources = load_curriculum_sources(pilot)
    ids = {s.get("source_id") for s in sources}
    assert "bj-g7-rational-2024" in ids
    assert "bj-g7-linear-eq-2024" in ids


def test_junior_high_answer_cites_b1_pack():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot), llm=None)
    session = SessionState(
        session_id="b1",
        profile=StudentProfile(region="北京", grade=7, age=13),
        phase=SessionPhase.IDLE,
    )
    reply = agent.chat(session, "什么是有理数？请讲一下")
    assert reply.intent == "answer"
    assert reply.citations, reply.reply
    assert any("有理数" in (c.title + c.excerpt) for c in reply.citations)
