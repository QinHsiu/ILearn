"""P7 tiered assignment: real papers + receipt."""

from ilearn.core.tier_suggest import classify_tiers, build_tier_assignment, materialize_tier_papers


def test_p7_tier_assignment_has_three_paper_drafts():
    tiers = classify_tiers(
        [
            {"name": "A", "avg_mastery": 0.2},
            {"name": "B", "avg_mastery": 0.5},
            {"name": "C", "avg_mastery": 0.9},
        ],
        weak_topic="小数乘法",
    )
    assignment = build_tier_assignment(tiers, topic="小数乘法")
    assert set(assignment.keys()) == {"basic", "advanced", "challenge"}
    assert assignment["basic"]["item_count"] >= 3
    assert assignment["challenge"]["difficulty"] == "hard"
    assert "小数乘法" in assignment["basic"]["title"]


def test_p7_materialize_papers_and_receipt():
    tiers = classify_tiers(
        [
            {"name": "A", "avg_mastery": 0.2},
            {"name": "B", "avg_mastery": 0.5},
            {"name": "C", "avg_mastery": 0.9},
        ],
        weak_topic="小数乘法",
    )
    papers, receipt = materialize_tier_papers(tiers, topic="小数乘法")
    assert set(papers.keys()) == {"basic", "advanced", "challenge"}
    assert len(papers["basic"]["items"]) >= 3
    assert papers["basic"]["items"][0]["answer_key"] is None
    assert receipt["status"] == "assigned"
    assert receipt["papers"]["basic"]["item_count"] == len(papers["basic"]["items"])
    assert papers["basic"]["items"][0]["source_refs"][0]["confidence"] >= 0.5
