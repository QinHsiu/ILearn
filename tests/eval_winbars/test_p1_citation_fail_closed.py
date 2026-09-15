"""P1 citation fail-closed win-bar tests."""

from ilearn.core.citation_gate import (
    CitationGateError,
    ensure_citations_or_stub,
    item_has_citation,
    item_has_formal_citation,
)
from ilearn.core.schemas import AssessmentItem, AssessmentPaper, ItemSourceRef


def _bare_item(item_id: str = "q1") -> AssessmentItem:
    return AssessmentItem(
        id=item_id,
        stem="1+1=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["kp1"],
        answer_key="2",
        source_refs=[],
    )


def test_p1_bare_item_gets_stub_citation():
    paper = AssessmentPaper(items=[_bare_item()], grade=5, curriculum_label="北京·人教")
    out = ensure_citations_or_stub(paper, fail_closed=True)
    assert item_has_citation(out.items[0])
    assert out.items[0].source_refs[0].example_answer is None
    assert out.items[0].source_refs[0].confidence is not None


def test_p1_existing_citation_preserved():
    item = _bare_item("q2")
    item.source_refs = [
        ItemSourceRef(example_id="ex1", curriculum_objective_ids=["obj1"])
    ]
    paper = AssessmentPaper(items=[item], grade=5, curriculum_label="北京·人教")
    out = ensure_citations_or_stub(paper, fail_closed=True)
    assert out.items[0].source_refs[0].example_id == "ex1"
    assert out.items[0].source_refs[0].confidence and out.items[0].source_refs[0].confidence >= 0.5
    assert item_has_formal_citation(out.items[0])


def test_p1_formal_strict_rejects_stub_only():
    # No knowledge_ids → only pending stub → formal_strict fails
    item = AssessmentItem(
        id="q1",
        stem="1+1=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=[],
        answer_key="2",
        source_refs=[],
    )
    paper = AssessmentPaper(items=[item], grade=5, curriculum_label="北京·人教")
    try:
        ensure_citations_or_stub(paper, fail_closed=True, formal_strict=True)
        raised = False
    except CitationGateError:
        raised = True
    assert raised


def test_p1_knowledge_ids_resolve_without_pending():
    paper = AssessmentPaper(items=[_bare_item()], grade=5, curriculum_label="北京·人教")
    out = ensure_citations_or_stub(paper, fail_closed=True, formal_strict=True)
    ref = out.items[0].source_refs[0]
    assert "pending" not in str(ref.curriculum_objective_ids).lower()
    assert ref.confidence and ref.confidence >= 0.5
    assert item_has_formal_citation(out.items[0])


def test_p1_fail_closed_raises_when_impossible(monkeypatch):
    def always_false(_item):
        return False

    monkeypatch.setattr(
        "ilearn.core.citation_gate.item_has_citation",
        always_false,
    )
    paper = AssessmentPaper(items=[_bare_item()], grade=5, curriculum_label="北京·人教")
    try:
        ensure_citations_or_stub(paper, fail_closed=True)
        raised = False
    except CitationGateError:
        raised = True
    assert raised
