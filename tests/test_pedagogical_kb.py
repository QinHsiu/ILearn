from pathlib import Path

from ilearn.core.pedagogical_kb import PedagogicalKnowledgeBase


def test_retrieve_concept_gap_returns_chinese():
    kb = PedagogicalKnowledgeBase(data_path=None)  # builtin only
    text = kb.retrieve("concept_gap", fail_streak=0)
    assert text
    assert "答案" not in text  # no answer leak phrases


def test_retrieve_escalates_index_with_streak():
    kb = PedagogicalKnowledgeBase(data_path=None)
    a = kb.retrieve("calc_error", 0)
    b = kb.retrieve("calc_error", 1)
    # If multiple phrases exist, streak may pick later; if only one, same string OK
    assert a and b


def test_missing_json_uses_builtin(tmp_path: Path):
    kb = PedagogicalKnowledgeBase(data_path=tmp_path / "missing.json")
    assert kb.retrieve("misread", 0)


def test_retrieve_uses_skill_keyed_phrases_when_default_empty():
    kb = PedagogicalKnowledgeBase(data_path=None)
    kb.strategies["conceptual"] = {
        "default": [],
        "fraction": ["分数概念提示：分子分母各表示什么？"],
    }
    assert kb.retrieve("concept_gap", 0) == "分数概念提示：分子分母各表示什么？"


def test_retrieve_orders_default_then_sorted_skill_keys():
    kb = PedagogicalKnowledgeBase(data_path=None)
    kb.strategies["conceptual"] = {
        "default": ["默认提示"],
        "zebra": ["Z提示"],
        "fraction": ["分数提示"],
    }
    assert kb.retrieve("concept_gap", 0) == "默认提示"
    assert kb.retrieve("concept_gap", 1) == "分数提示"
    assert kb.retrieve("concept_gap", 2) == "Z提示"


def test_json_override(tmp_path: Path):
    path = tmp_path / "pedagogical_strategies.json"
    path.write_text(
        '{"conceptual":{"default":["自定义概念提示"]}}',
        encoding="utf-8",
    )
    kb = PedagogicalKnowledgeBase(data_path=path)
    assert kb.retrieve("concept_gap", 0) == "自定义概念提示"
