from pathlib import Path

from ilearn.core.schemas import StudentProfile
from ilearn.providers.retriever import get_retriever

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_get_retriever_keyword_returns_beijing_hits():
    r = get_retriever("keyword", PILOT)
    cites = r.retrieve(
        StudentProfile(region="北京", grade=5, age=11),
        "分数加减",
        top_k=3,
    )
    assert len(cites) >= 1


def test_get_retriever_unknown_backend_raises():
    import pytest

    with pytest.raises(ValueError, match="unknown retriever backend"):
        get_retriever("invalid", PILOT)
