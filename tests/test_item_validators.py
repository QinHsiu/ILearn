"""Tests for four-dimension item validators and single revise pass."""

from __future__ import annotations

from pathlib import Path
from random import Random

import pytest

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.core.item_validators import (
    ValidationIssue,
    revise_paper_once,
    validate_paper,
)
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
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


def test_situation_tag_passes_authenticity():
    paper = _paper(
        _item(
            stem="计算：125 + 375 = ?",
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


def test_authenticity_only_issues_do_not_revise():
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    profile = StudentProfile(region="北京", grade=5, age=11)
    item = _item(stem="计算：125 + 375 = ?", situation_tag=None)
    paper = _paper(item, grade=5)
    issues = validate_paper(paper, grade=5)
    assert any(issue.dimension == "authenticity" for issue in issues)
    hard_issues = [issue for issue in issues if issue.dimension != "authenticity"]
    assert not hard_issues
    revised = revise_paper_once(
        paper,
        hard_issues,
        profile=profile,
        curriculum=curriculum,
        rng=Random(0),
    )
    assert revised.items[0].id == item.id
    assert revised.items[0].stem == item.stem


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
    orchestrator.generate_assessment(session_id)
    decisions = store.load(session_id).decision_log
    assert any(decision.agent == "item_validators" for decision in decisions)


def test_validation_issue_fields():
    issue = ValidationIssue(
        item_id="x__00",
        dimension="solvability",
        message="missing answer_key",
    )
    assert issue.item_id == "x__00"
    assert issue.dimension == "solvability"
    assert issue.message
