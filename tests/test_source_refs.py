import json
from pathlib import Path

from ilearn.agents.assessment import (
    AssessmentAgent,
    bind_citations_to_item,
    bind_source_refs_to_item,
)
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.report import format_source_ref_lines, render_full_report
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    CurriculumCitation,
    GradeResult,
    ItemSourceRef,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider, load_example_bank
from ilearn.web.app import wrong_item_source_entries

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _citations() -> list[CurriculumCitation]:
    return [
        CurriculumCitation(
            citation_id="frac-src",
            source_id="frac-src",
            title="分数加减法课标要点",
            excerpt="同分母分数加减：分母不变，分子相加减。",
            source_label="北京·人教",
        ),
        CurriculumCitation(
            citation_id="dec-src",
            source_id="dec-src",
            title="小数加减运算",
            excerpt="小数加减竖式计算，注意小数点对齐。",
            source_label="北京·人教",
        ),
    ]


def test_item_source_ref_schema_fields():
    ref = ItemSourceRef(
        example_id="ex-frac-1",
        curriculum_objective_ids=["bj-g5-frac-01"],
        textbook_chapter="五年级上册 第3章",
        source_label="北京·人教·小学数学",
    )
    assert ref.example_id == "ex-frac-1"
    assert ref.curriculum_objective_ids == ["bj-g5-frac-01"]
    assert ref.textbook_chapter.startswith("五年级")
    assert ref.source_label


def test_example_bank_covers_pilot_knowledge_ids():
    bank = load_example_bank(PILOT)
    knowledge_ids = {
        row["id"]
        for row in json.loads((PILOT / "knowledge.json").read_text(encoding="utf-8"))
    }
    assert knowledge_ids
    for knowledge_id in knowledge_ids:
        assert bank.get(knowledge_id), f"missing examples for {knowledge_id}"


def test_bind_source_refs_merges_example_and_citations():
    bank = load_example_bank(PILOT)
    item = AssessmentItem(
        id="i1",
        stem="计算同分母分数相加",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
    )
    refs = bind_source_refs_to_item(item, _citations(), bank)
    assert refs
    ref = refs[0]
    assert ref.example_id
    assert ref.curriculum_objective_ids
    assert ref.textbook_chapter
    assert ref.source_label


def test_assessment_agent_populates_source_refs_for_pilot_grade():
    profile = StudentProfile(region="北京", grade=5, age=11)
    cur = CurriculumAgent(pilot_dir=PILOT).run(
        AgentContext(session_id="s1", phase=SessionPhase.ONBOARD, profile=profile)
    )
    citations = cur.payload.get("citations") or []
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=profile,
        metadata={"citations": citations, "weak_knowledge_ids": []},
    )
    paper = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT)).run(ctx).payload["paper"]
    assert paper.items
    assert all(item.source_refs for item in paper.items)
    assert all(ref.example_id or ref.curriculum_objective_ids for ref in paper.items[0].source_refs)


def test_render_full_report_includes_wrong_item_sources():
    profile = StudentProfile(region="北京", grade=5, age=11)
    item = AssessmentItem(
        id="r1",
        stem="计算 1/4 + 2/4",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
        source_refs=[
            ItemSourceRef(
                example_id="ex-frac-add-1",
                curriculum_objective_ids=["bj-g5-frac-01"],
                textbook_chapter="五年级上册 第3章 分数加减",
                source_label="北京·人教·小学数学",
            )
        ],
    )
    paper = AssessmentPaper(
        items=[item],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    grades = [
        GradeResult(
            item_id="r1",
            final_correct=False,
            knowledge_ids=["frac_add_same"],
            error_tags=["concept_gap"],
        ),
    ]
    session = SessionState(
        session_id="test-session",
        profile=profile,
        paper=paper,
        grades=grades,
    )
    md = render_full_report(session)
    assert "错题参考来源" in md
    assert "ex-frac-add-1" in md
    assert "bj-g5-frac-01" in md


def test_format_source_ref_lines_and_wrong_item_entries():
    ref = ItemSourceRef(
        example_id="ex-1",
        curriculum_objective_ids=["obj-1"],
        textbook_chapter="第2章",
        source_label="北京·人教",
    )
    lines = format_source_ref_lines(ref)
    assert any("例题" in line for line in lines)
    assert any("课标" in line for line in lines)

    session = {
        "paper": {
            "items": [
                {
                    "id": "q1",
                    "stem": "测试题",
                    "source_refs": [
                        {
                            "example_id": "ex-1",
                            "curriculum_objective_ids": ["obj-1"],
                            "textbook_chapter": "第2章",
                            "source_label": "北京·人教",
                        }
                    ],
                }
            ]
        },
        "grades": [{"item_id": "q1", "final_correct": False}],
    }
    entries = wrong_item_source_entries(session)
    assert len(entries) == 1
    assert entries[0]["item_id"] == "q1"
    assert entries[0]["source_lines"]


def test_bind_citations_still_returns_objective_ids():
    item = AssessmentItem(
        id="i1",
        stem="计算同分母分数相加",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
    )
    ids = bind_citations_to_item(item, _citations())
    assert ids
    assert ids[0] == "frac-src"
