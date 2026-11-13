"""P4 L2 wiki — BM25 + skill boost + companion merge."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.companion import CompanionAgent
from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.core.state_event import StateEvent
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.learner_state_store import LearnerStateStore
from ilearn.wiki.bm25 import BM25Index, tokenize
from ilearn.wiki.ingest import ingest_pilot_wiki, pages_from_concept_assets
from ilearn.wiki.models import WikiPage
from ilearn.wiki.retrieve import retrieve_wiki
from ilearn.wiki.store import WikiStore


def test_bm25_ranks_relevant_doc():
    corpus = [
        tokenize("同分母分数加减 分母不变"),
        tokenize("三位数乘两位数 竖式"),
        tokenize("有理数 数轴 绝对值"),
    ]
    index = BM25Index(corpus)
    ranked = index.rank(tokenize("分数加减"), top_k=2)
    assert ranked
    assert ranked[0][0] == 0


def test_ingest_and_search(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    store = WikiStore(tmp_path / "wiki")
    stats = ingest_pilot_wiki(store, pilot)
    assert stats["pages"] >= 5
    hits = store.search_bm25("分数加减", top_k=3)
    assert hits
    assert any("分数" in h[0].title or "分数" in h[0].body for h in hits)


def test_skill_boost_prefers_weak_mastery(tmp_path: Path):
    store = WikiStore(tmp_path / "wiki")
    store.upsert_many(
        [
            WikiPage(
                page_id="p1",
                title="分数通分",
                body="异分母分数先通分再加减",
                skill_ids=["kw:通分", "frac"],
            ),
            WikiPage(
                page_id="p2",
                title="面积公式",
                body="长方形面积等于长乘宽",
                skill_ids=["kw:面积"],
            ),
        ]
    )
    store.rebuild_skill_graph()
    state = LearnerState(
        learner_id="n",
        mastery={
            "frac": MasteryEstimate(skill_id="frac", mastery=0.2, evidence_count=2),
        },
    ).seal_initial()
    hits = retrieve_wiki(store, "怎么算", learner_state=state, top_k=2)
    assert hits
    assert hits[0].page.page_id == "p1"
    assert "frac" in hits[0].matched_skills or hits[0].matched_skills


def test_companion_answer_can_cite_wiki(tmp_path: Path):
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    wiki = WikiStore(tmp_path / "wiki")
    ingest_pilot_wiki(wiki, pilot)
    learners = LearnerStateStore(tmp_path / "learners")
    agent = CompanionAgent(
        PilotBeijingRenjiaoProvider(pilot),
        llm=None,
        wiki_store=wiki,
        learner_store=learners,
    )
    session = SessionState(
        session_id="w1",
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="wiki_user"),
        phase=SessionPhase.IDLE,
    )
    # Seed weak skill overlapping wiki keywords
    lid = "nick:wiki_user"
    s0 = learners.load(lid)
    learners.append(
        lid,
        StateEvent(
            learner_id=lid,
            event_type="mastery.update",
            payload={"skill_id": "kw:分数", "mastery": 0.25},
            prev_state_hash=s0.state_hash,
        ),
    )
    reply = agent.chat(session, "什么是同分母分数加减？请讲一下")
    assert reply.intent == "answer"
    assert reply.citations
    assert any(
        "wiki" in (c.source_label or "") or "分数" in c.title or "分数" in c.excerpt
        for c in reply.citations
    )


def test_concept_pages_ingested():
    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    pages = pages_from_concept_assets(pilot)
    assert any("concept:" in p.skill_ids[0] for p in pages if p.skill_ids)
