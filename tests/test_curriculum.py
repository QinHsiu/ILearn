import math
import random
from pathlib import Path

from ilearn.providers.curriculum import (
    PilotBeijingRenjiaoProvider,
    eval_answer_expr,
    fill_slots,
    fill_template_slots,
    render_choices,
    render_template,
    render_template_text,
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
    rng = random.Random(42)
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
    assert eval_answer_expr("frac(a+b, d)", values) == "2"


def test_answer_expr_string_literal():
    assert eval_answer_expr("平行", {}) == "平行"
    assert eval_answer_expr('"平行"', {}) == "平行"


def test_g4_easy_fill_08_string_answer():
    p = PilotBeijingRenjiaoProvider(ROOT)
    record = p.get_template_record("g4_easy_fill_08")
    assert eval_answer_expr(record["answer_expr"], {}) == "平行"


def test_g6_easy_fill_08_fruit_boxes_are_a_valid_gcd_story():
    p = PilotBeijingRenjiaoProvider(ROOT)
    record = p.get_template_record("g6_easy_fill_08")
    stem = record["stem_template"]
    assert "苹果" in stem and "梨" in stem
    assert "最多能装" in stem
    assert "最大公因数" not in stem
    rng = random.Random(0)
    for _ in range(30):
        values = fill_template_slots(record, rng)
        a, b = int(values["a"]), int(values["b"])
        assert a != b
        assert math.gcd(a, b) >= 2
        answer = eval_answer_expr(record["answer_expr"], values)
        assert int(answer) == math.gcd(a, b)
        rendered = render_template_text(stem, values)
        assert f"{a}个苹果" in rendered
        assert f"{b}个梨" in rendered


def test_g4_hard_fill_20_coupled_slots():
    p = PilotBeijingRenjiaoProvider(ROOT)
    record = p.get_template_record("g4_hard_fill_20")
    rng = random.Random(0)
    for _ in range(20):
        values = fill_template_slots(record, rng)
        assert values["p"] == values["k"] * values["b"]
        answer = eval_answer_expr(record["answer_expr"], values)
        assert answer.isdigit()
        assert int(answer) == values["k"]


def test_frac_answer_simplified():
    values = {"a": 1, "b": 1, "d": 3}
    assert eval_answer_expr("frac(a+b, d)", values) == "2/3"


def test_render_template_text_with_expressions():
    values = {"a": 20, "b": 8}
    text = render_template_text("宽={a//2}，和={a+b}", values)
    assert text == "宽=10，和=28"


def test_render_choices_with_ans_and_exprs():
    values = {"a": 3, "b": 5, "d": 4}
    answer = eval_answer_expr("frac(a+b, d)", values)
    choices = render_choices(
        ["{ans}", "{a+b}", "{a}/{d}", "{a//2}"],
        values,
        answer=answer,
    )
    assert choices[0] == "2"
    assert choices[1] == "8"
    assert choices[2] == "3/4"
    assert choices[3] == "1"
