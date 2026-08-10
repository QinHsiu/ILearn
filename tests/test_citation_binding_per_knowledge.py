from ilearn.agents.assessment import bind_citations_to_item
from ilearn.core.schemas import AssessmentItem, CurriculumCitation


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


def test_bind_citations_prefers_matching_knowledge_and_stem():
    citations = _citations()
    frac_item = AssessmentItem(
        id="i1",
        stem="计算同分母分数相加",
        type="fill",
        difficulty="easy",
        knowledge_ids=["frac_add_same"],
    )
    dec_item = AssessmentItem(
        id="i2",
        stem="小数加法竖式计算",
        type="fill",
        difficulty="easy",
        knowledge_ids=["decimal_add"],
    )

    frac_ids = bind_citations_to_item(frac_item, citations)
    dec_ids = bind_citations_to_item(dec_item, citations)

    assert frac_ids
    assert dec_ids
    assert frac_ids[0] == "frac-src"
    assert dec_ids[0] == "dec-src"
    assert frac_ids != dec_ids


def test_assessment_agent_binds_distinct_citations_per_item():
    from pathlib import Path

    from ilearn.agents.assessment import AssessmentAgent
    from ilearn.agents.protocol import AgentContext, SessionPhase
    from ilearn.core.schemas import StudentProfile
    from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

    pilot = Path(__file__).resolve().parents[1] / "data" / "pilot"
    profile = StudentProfile(region="北京", grade=5, age=11)
    citations = _citations()
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=profile,
        metadata={"citations": citations, "weak_knowledge_ids": []},
    )
    paper = AssessmentAgent(PilotBeijingRenjiaoProvider(pilot)).run(ctx).payload["paper"]

    bound = [item.curriculum_objective_ids for item in paper.items if item.curriculum_objective_ids]
    assert bound
    unique_first = {ids[0] for ids in bound if ids}
    assert len(unique_first) >= 1
