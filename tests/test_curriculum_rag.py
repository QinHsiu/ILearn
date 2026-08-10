from pathlib import Path

from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum_rag import CurriculumRagRetriever

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_retriever_returns_beijing_grade5_on_fraction_query():
    retriever = CurriculumRagRetriever(pilot_dir=PILOT)
    cites = retriever.retrieve(
        StudentProfile(region="北京", grade=5, age=11),
        query="分数加减",
        top_k=3,
    )
    assert len(cites) >= 1
    assert cites[0].source_label
    assert any("分数" in c.title or "分数" in c.excerpt for c in cites)


def test_retriever_filters_by_grade():
    retriever = CurriculumRagRetriever(pilot_dir=PILOT)
    cites = retriever.retrieve(
        StudentProfile(region="北京", grade=4, age=10),
        query="加减法",
        top_k=5,
    )
    assert len(cites) >= 1
    assert all("四" in c.title or "加减" in c.excerpt for c in cites)


def test_retriever_limits_non_beijing_to_two():
    retriever = CurriculumRagRetriever(pilot_dir=PILOT)
    cites = retriever.retrieve(
        StudentProfile(region="上海", grade=5, age=11),
        query="分数",
        top_k=5,
    )
    assert len(cites) <= 2


def test_token_overlap_scoring_prefers_matching_keywords():
    retriever = CurriculumRagRetriever(pilot_dir=PILOT)
    cites = retriever.retrieve(
        StudentProfile(region="北京", grade=5, age=11),
        query="同分母分数",
        top_k=2,
    )
    assert cites[0].title
