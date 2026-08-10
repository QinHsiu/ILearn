from pathlib import Path

from ilearn.providers.curriculum import (
    PilotBeijingRenjiaoProvider,
    eval_answer_expr,
    fill_slots,
    render_template,
)

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_provider_label():
    p = PilotBeijingRenjiaoProvider(ROOT)
    assert p.label == "北京·人教·小学数学"


def test_knowledge_nodes_per_grade():
    p = PilotBeijingRenjiaoProvider(ROOT)
    for g in (4, 5, 6):
        nodes = p.list_knowledge(g)
        assert len(nodes) >= 4
        assert all(n.grade == g for n in nodes)


def test_grade5_has_enough_templates_for_mix():
    p = PilotBeijingRenjiaoProvider(ROOT)
    # Need enough distinct templates to build 10 easy / 8 medium / 2 hard and 8/8/4 types
    for g in (4, 5, 6):
        t = p.list_templates(g)
        assert len(t) >= 20
        assert {x.difficulty for x in t} >= {"easy", "medium", "hard"}
        assert {x.item_type for x in t} >= {"choice", "fill", "constructed"}


def test_list_templates_filters():
    p = PilotBeijingRenjiaoProvider(ROOT)
    easy = p.list_templates(5, difficulty="easy")
    assert easy
    assert all(t.difficulty == "easy" for t in easy)
    choice = p.list_templates(5, item_type="choice")
    assert choice
    assert all(t.item_type == "choice" for t in choice)


def test_slot_renderer_int_and_choice():
    rng = __import__("random").Random(42)
    values = fill_slots(
        {"a": "int:1-8", "b": "int:1-8", "d": "choice:2,4,5,8"},
        rng,
    )
    assert 1 <= values["a"] <= 8
    assert 1 <= values["b"] <= 8
    assert values["d"] in {"2", "4", "5", "8"}
    stem = render_template("计算：{a}/{d} + {b}/{d} = ?", values)
    assert "/" in stem and "+" in stem


def test_answer_expr_eval():
    values = {"a": 3, "b": 5, "d": 4}
    assert eval_answer_expr("(a+b)/d", values) == "2"
