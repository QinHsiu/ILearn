"""Edition 0830_5 D — explainer, tiered interventions, cycle hard-fail, locks."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from ilearn.core.cognitive_profile import CognitiveSkillGraph
from ilearn.core.diagnosis_explainer import DiagnosisExplainer
from ilearn.core.intervention_library import get_tiered_intervention
from ilearn.core.schemas import StudentProfile
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore


def test_diagnosis_explainer_attribution():
    text = DiagnosisExplainer.explain_attribution(
        "frac_add_same", "concept_gap", wrong_count=2
    )
    assert "同分母分数加法" in text
    assert "frac_add_same" not in text
    assert "概念" in text


def test_build_explanations_includes_findings():
    rows = DiagnosisExplainer.build_explanations(
        weak_skills=["frac_add_same"],
        error_attribution={"top_tags": ["calc_error"], "counts": {"calc_error": 3}},
        cognitive_findings=[
            {
                "gap_skill": "frac_meaning_001",
                "root_cause": "前置技能缺失",
                "recommendation": "请先复习分数单位",
            }
        ],
    )
    assert any("理解分数单位" in r for r in rows)
    assert not any("frac_meaning_001" in r for r in rows)
    assert any("计算" in r or "步骤" in r for r in rows)


def test_build_explanations_dedupes_duplicate_cognitive_findings():
    dup_finding = {
        "gap_skill_label": "理解分数单位",
        "gap_skill": "frac_meaning_001",
        "root_cause": "理解层次不足",
        "recommendation": "建议用自己的话解释概念，并对照图形/例题核对理解。",
    }
    rows = DiagnosisExplainer.build_explanations(
        weak_skills=["frac_mult"],
        error_attribution={"top_tags": [], "counts": {}},
        cognitive_findings=[dup_finding, dup_finding, dup_finding],
    )
    expected = (
        "技能「理解分数单位」：理解层次不足。"
        "建议用自己的话解释概念，并对照图形/例题核对理解。"
    )
    assert rows.count(expected) == 1


def test_tiered_intervention_by_mastery():
    assert get_tiered_intervention("frac_add_same", 0.85) is None
    t1 = get_tiered_intervention("frac_add_same", 0.7)
    assert t1 is not None and t1["tier"] == "tier_1"
    t2 = get_tiered_intervention("frac_add_same", 0.5)
    assert t2 is not None and t2["tier"] == "tier_2"
    t3 = get_tiered_intervention("frac_add_same", 0.2)
    assert t3 is not None and t3["tier"] == "tier_3"
    assert "prerequisite_chain" in t3


def test_cognitive_graph_hard_fails_on_cycle(tmp_path: Path):
    bad = {
        "skills": [
            {
                "skill_id": "a",
                "name": "A",
                "knowledge_point": "u",
                "dimension": "remember",
                "prerequisites": ["b"],
                "grade": 4,
            },
            {
                "skill_id": "b",
                "name": "B",
                "knowledge_point": "u",
                "dimension": "remember",
                "prerequisites": ["a"],
                "grade": 4,
            },
        ]
    }
    path = tmp_path / "cycle.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="circular"):
        CognitiveSkillGraph(path)


def test_llm_fallback_depth_exhausted():
    client = LLMClient(api_key=None)
    client._fallback_depth = LLMClient._MAX_FALLBACK_DEPTH
    data = client.chat_json("x", "y", fallback=True)
    assert data.get("fallback_exhausted") is True


def test_session_store_per_session_locks(tmp_path: Path):
    store = SessionStore(tmp_path, cache_ttl=60)
    a = store.create(StudentProfile(region="北京", grade=5, age=11))
    b = store.create(StudentProfile(region="北京", grade=5, age=11))
    assert store._lock_for(a.session_id) is store._lock_for(a.session_id)
    assert store._lock_for(a.session_id) is not store._lock_for(b.session_id)

    errors: list[BaseException] = []

    def _hammer(sid: str) -> None:
        try:
            for _ in range(20):
                state = store.load(sid)
                store.save(state)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=_hammer, args=(a.session_id,)),
        threading.Thread(target=_hammer, args=(b.session_id,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
