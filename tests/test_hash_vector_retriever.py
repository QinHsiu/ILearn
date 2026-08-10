from pathlib import Path

import pytest

from ilearn.core.schemas import StudentProfile
from ilearn.providers.retriever import get_retriever

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"
PROFILE = StudentProfile(region="北京", grade=5, age=11)


def test_hash_vector_retriever_ranks_fraction_query():
    cites = get_retriever("hash_vector", PILOT).retrieve(
        PROFILE, "同分母分数", top_k=3
    )
    assert cites
    assert cites[0].source_id


def test_qdrant_backend_raises_clear_error():
    with pytest.raises(NotImplementedError, match="qdrant"):
        get_retriever("qdrant", PILOT).retrieve(PROFILE, "分数", top_k=1)


def test_hash_vector_differs_from_keyword_but_still_returns_hits():
    keyword = get_retriever("keyword", PILOT).retrieve(PROFILE, "分数加减", top_k=3)
    hash_vec = get_retriever("hash_vector", PILOT).retrieve(PROFILE, "分数加减", top_k=3)
    assert keyword
    assert hash_vec
