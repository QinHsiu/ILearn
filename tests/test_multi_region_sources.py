from pathlib import Path

from ilearn.core.schemas import StudentProfile
from ilearn.providers.retriever import get_retriever

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_shanghai_profile_retrieves_shanghai_sources():
    cites = get_retriever("keyword", PILOT).retrieve(
        StudentProfile(region="上海", grade=5, age=11),
        "分数",
        top_k=3,
    )
    assert cites
    assert any(
        "上海" in (c.source_label or "") or "sh-" in (c.source_id or "")
        for c in cites
    )


def test_beijing_profile_still_retrieves_beijing_sources():
    cites = get_retriever("keyword", PILOT).retrieve(
        StudentProfile(region="北京", grade=5, age=11),
        "分数加减",
        top_k=3,
    )
    assert cites
    assert all(
        "bj-" in (c.source_id or "") or "北京" in (c.source_label or "")
        for c in cites
    )
