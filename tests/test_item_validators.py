"""Tests for four-dimension item validators and single revise pass."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.item_validators import (
    ValidationIssue,
    _LIFE_CONTEXT_KEYWORDS,
    revise_paper_once,
    validate_paper,
)
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _item(**overrides) -> AssessmentItem:
    base = dict(
        id="tpl_a__00",
        stem="小明买了3个苹果，一共花了12元。",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
        answer_key="12",
    )
    base.update(overrides)
    return AssessmentItem(**base)


def _paper(*items: AssessmentItem, grade: int = 5) -> AssessmentPaper:
    return AssessmentPaper(
        items=list(items),
        grade=grade,  # type: ignore[arg-type]
        curriculum_label="test",
    )


def test_empty_answer_key_raises_solvability():
    paper = _paper(_item(answer_key=None))
    issues = validate_paper(paper, grade=5)
    assert any(
        issue.dimension == "solvability" and issue.item_id == "tpl_a__00"
        for issue in issues
    )


def test_huge_number_raises_realism():
    paper = _paper(
        _item(stem="某仓库有999999999个零件，每次运走1000个，需要多少次？")
    )
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "realism" for issue in issues)


def test_overlong_stem_raises_readability():
    long_stem = "阅读" + ("这是一段很长的题干。" * 30)
    paper = _paper(_item(stem=long_stem))
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "readability" for issue in issues)


def test_missing_situation_and_keywords_raises_authenticity():
    paper = _paper(
        _item(
            stem="计算：125 + 375 = ?",
            situation_tag=None,
        )
    )
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "authenticity" for issue in issues)


def test_situation_tag_without_keywords_fails_authenticity():
    paper = _paper(
        _item(
            stem="计算：125 + 375 = ?",
            situation_tag="life",
        )
    )
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "authenticity" for issue in issues)


def test_life_keywords_pass_authenticity():
    paper = _paper(
        _item(
            stem="小明在学校商店买了3个苹果，一共花了12元。",
            situation_tag="life",
        )
    )
    issues = validate_paper(paper, grade=5)
    assert not any(issue.dimension == "authenticity" for issue in issues)


def test_constructed_requires_rubric_for_solvability():
    paper = _paper(
        _item(
            type="constructed",
            answer_key=None,
            rubric_steps=[],
        )
    )
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "solvability" for issue in issues)


def test_revise_paper_once_replaces_unsolvable_item():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    profile = StudentProfile(region="北京", grade=5, age=11)
    bad = _item(id="g5_easy_fill_01__00", answer_key=None)
    paper = _paper(bad, grade=5)
    issues = validate_paper(paper, grade=5)
    revised = revise_paper_once(
        paper,
        issues,
        profile=profile,
        curriculum=curriculum,
        rng=Random(0),
    )
    assert len(revised.items) == 1
    assert revised.items[0].answer_key


def test_authenticity_issues_revise_once():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    profile = StudentProfile(region="北京", grade=5, age=11)
    item = _item(
        id="g5_easy_fill_05__00",
        stem="计算：125 + 375 = ?",
        situation_tag=None,
    )
    paper = _paper(item, grade=5)
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "authenticity" for issue in issues)
    revised = revise_paper_once(
        paper,
        issues,
        profile=profile,
        curriculum=curriculum,
        rng=Random(0),
    )
    assert revised.items[0].id != item.id
    assert any(keyword in revised.items[0].stem for keyword in _LIFE_CONTEXT_KEYWORDS)


def test_orchestrator_appends_item_validators_decision(tmp_path):
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    paper = orchestrator.generate_assessment(session_id)
    session = store.load(session_id)
    decisions = session.decision_log
    assert any(decision.agent == "item_validators" for decision in decisions)
    validator = next(d for d in decisions if d.agent == "item_validators")
    assert "authenticity soft only" not in validator.reason
    issues = validate_paper(paper, grade=5)
    assert not any(issue.dimension == "authenticity" for issue in issues)
    assert all(item.situation_tag and item.situation_tag != "neutral" for item in paper.items)


def test_pilot_templates_declare_situation_and_life_context():
    raw = json.loads((PILOT / "templates.json").read_text(encoding="utf-8"))
    allowed = {"sports", "games", "life", "science"}
    for template in raw:
        assert template.get("situation_tag") in allowed, template["id"]
        stem = template["stem_template"]
        assert any(keyword in stem for keyword in _LIFE_CONTEXT_KEYWORDS), template["id"]


def test_practice_loop_validates_and_logs_revision(tmp_path):
    store = SessionStore(tmp_path)
    orchestrator = MultiAgentOrchestrator(
        store=store,
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    session_id = orchestrator.create_session(
        StudentProfile(region="北京", grade=5, age=11)
    )
    session = store.load(session_id)
    session.diagnosis = DiagnosisReport(
        curriculum_label="pilot",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="frac_add_same",
                score_rate=0.0,
                level="weak",
                item_ids=["i"],
            )
        ],
    )
    store.save(session)

    orchestrator.start_practice_loop(session_id)

    decision = store.load(session_id).decision_log[-1]
    assert decision.agent == "item_validators"
    assert "validated paper" in decision.reason
    assert "remaining" in decision.reason


def test_validation_issue_fields():
    issue = ValidationIssue(
        item_id="x__00",
        dimension="solvability",
        message="missing answer_key",
    )
    assert issue.item_id == "x__00"
    assert issue.dimension == "solvability"
    assert issue.message
