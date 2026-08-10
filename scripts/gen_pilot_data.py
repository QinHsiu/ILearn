"""One-off generator for data/pilot/knowledge.json and templates.json."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pilot"

KNOWLEDGE = [
    {"id": "mult_3digit", "grade": 4, "name": "三位数乘两位数", "ability_tags": ["mental_math"]},
    {"id": "rect_area", "grade": 4, "name": "长方形面积", "ability_tags": ["spatial"]},
    {"id": "angle_measure", "grade": 4, "name": "角的度量", "ability_tags": ["spatial"]},
    {"id": "parallel_perp", "grade": 4, "name": "平行与垂直", "ability_tags": ["logic"]},
    {"id": "dec_mult", "grade": 5, "name": "小数乘法", "ability_tags": ["mental_math"]},
    {"id": "frac_add_same", "grade": 5, "name": "同分母分数加法", "ability_tags": ["logic"]},
    {"id": "frac_mult", "grade": 5, "name": "分数乘法", "ability_tags": ["logic"]},
    {"id": "simple_eq", "grade": 5, "name": "简易方程", "ability_tags": ["logic"]},
    {"id": "frac_div", "grade": 6, "name": "分数除法", "ability_tags": ["logic"]},
    {"id": "ratio", "grade": 6, "name": "比和比例", "ability_tags": ["logic"]},
    {"id": "circle_area", "grade": 6, "name": "圆的面积", "ability_tags": ["spatial"]},
    {"id": "percent", "grade": 6, "name": "百分数应用", "ability_tags": ["mental_math"]},
    {"id": "factors", "grade": 6, "name": "因数与倍数", "ability_tags": ["logic"]},
]

MIX = [
    ("easy", "choice", 4),
    ("easy", "fill", 4),
    ("easy", "constructed", 2),
    ("medium", "choice", 3),
    ("medium", "fill", 3),
    ("medium", "constructed", 2),
    ("hard", "choice", 1),
    ("hard", "fill", 1),
]

STEMS: dict[int, dict[tuple[str, str], list[tuple]]] = {
    4: {
        ("easy", "choice"): [
            ("rect_area", "长方形长{a}cm、宽{b}cm，面积是多少平方厘米？", {"a": "int:3-12", "b": "int:2-10"}, "a*b", ["{ans}", "{a}+{b}", "{a*b+2}", "{a*b-2}"], ["面积=长×宽", "代入计算"]),
            ("mult_3digit", "计算：{a} × {b} = ?", {"a": "int:12-99", "b": "int:2-9"}, "a*b", ["{ans}", "{a+b}", "{a*b+10}", "{a*b-10}"], ["列竖式或口算", "核对进位"]),
            ("angle_measure", "一个锐角是{a}°，一个直角是90°，两角之和是多少度？", {"a": "int:10-80"}, "a+90", ["{ans}", "{a}", "180", "90"], ["识别角类型", "相加"]),
            ("parallel_perp", "两条直线互相垂直，其中一个角是90°，相邻角是多少度？", {}, "90", ["90", "180", "45", "60"], ["垂直定义", "相邻角互补"]),
        ],
        ("easy", "fill"): [
            ("rect_area", "正方形边长{a}cm，周长是___cm。", {"a": "int:3-15"}, "a*4", None, ["周长=4×边长"]),
            ("mult_3digit", "{a} × 10 = ___", {"a": "int:11-99"}, "a*10", None, ["末尾补零"]),
            ("angle_measure", "平角的一半是___度。", {}, "90", None, ["平角180°"]),
            ("parallel_perp", "同一平面内，永不相交的两条直线叫做___线。", {}, "平行", None, ["平行线定义"]),
        ],
        ("easy", "constructed"): [
            ("rect_area", "长方形长{a}cm、宽{b}cm，先写面积公式再求面积。", {"a": "int:4-10", "b": "int:3-8"}, "a*b", None, ["写出S=ab", "代入", "得数"]),
            ("mult_3digit", "用竖式计算 {a} × {b}，写出最后结果。", {"a": "int:12-45", "b": "int:12-45"}, "a*b", None, ["竖式对齐", "分步相乘", "相加"]),
        ],
        ("medium", "choice"): [
            ("rect_area", "长方形周长{a}cm，长{b}cm，宽是多少厘米？", {"a": "int:20-40", "b": "int:5-12"}, "(a-2*b)/2", ["{ans}", "{b}", "{a-b}", "{a//2}"], ["周长公式", "解宽"]),
            ("mult_3digit", "估算：{a} × {b} 最接近哪个数？", {"a": "int:198-502", "b": "int:3-8"}, "round(a)*round(b)", ["{ans}", "{a}", "{b}", "{a+b}"], ["四舍五入", "估算相乘"]),
            ("angle_measure", "三角形两角分别是{a}°和{b}°，第三个角是多少度？", {"a": "int:30-70", "b": "int:30-70"}, "180-a-b", ["{ans}", "{a+b}", "90", "360"], ["内角和180°", "减法"]),
        ],
        ("medium", "fill"): [
            ("rect_area", "长{a}cm、宽{b}cm的长方形面积是___cm²。", {"a": "int:4-9", "b": "int:4-9"}, "a*b", None, ["面积公式"]),
            ("mult_3digit", "{a} × {b} + {c} = ___", {"a": "int:11-30", "b": "int:11-30", "c": "int:1-20"}, "a*b+c", None, ["先乘后加"]),
            ("angle_measure", "钟面上3:00时，时针与分针所成较小角是___度。", {}, "90", None, ["读钟面角"]),
        ],
        ("medium", "constructed"): [
            ("parallel_perp", "画一个长{a}cm、宽{b}cm的长方形，标出长宽并求面积。", {"a": "int:5-8", "b": "int:3-6"}, "a*b", None, ["作图", "标注", "计算"]),
            ("mult_3digit", "学校买了{a}盒铅笔，每盒{b}支，一共多少支？列式计算。", {"a": "int:12-30", "b": "int:12-24"}, "a*b", None, ["理解题意", "列式", "计算"]),
        ],
        ("hard", "choice"): [
            ("rect_area", "两个长{a}cm、宽{b}cm的长方形拼成长方形（不重叠），最小周长是多少厘米？", {"a": "int:4-8", "b": "int:3-6"}, "2*(a+2*b)", ["{ans}", "2*(a+b)", "a*b", "4*a"], ["拼法分析", "周长"]),
        ],
        ("hard", "fill"): [
            ("mult_3digit", "□ × {b} = {p}，□ = ___", {"b": "int:12-24", "p": "int:144-576"}, "p/b", None, ["逆运算"]),
        ],
    },
    5: {
        ("easy", "choice"): [
            ("frac_add_same", "计算：{a}/{d} + {b}/{d} = ?", {"a": "int:1-8", "b": "int:1-8", "d": "choice:2,4,5,8"}, "(a+b)/d", ["{ans}", "{a+b}", "{a}/{d}", "{b}/{d}"], ["同分母相加", "化简"]),
            ("dec_mult", "计算：{a}.{b} × 10 = ?", {"a": "int:1-9", "b": "int:1-9"}, "a*10+b", ["{ans}", "{a}.{b}", "{a}+{b}", "10"], ["小数点右移"]),
            ("frac_mult", "计算：{a}/{d} × {b} = ?", {"a": "int:1-5", "b": "int:2-6", "d": "choice:2,4,5,8"}, "a*b/d", ["{ans}", "{a+b}", "{a}/{d}", "{b}"], ["分数乘整数", "约分"]),
            ("simple_eq", "若 x + {a} = {b}，则 x = ?", {"a": "int:1-20", "b": "int:21-50"}, "b-a", ["{ans}", "{a}", "{b}", "{a+b}"], ["移项", "减法"]),
        ],
        ("easy", "fill"): [
            ("frac_add_same", "{a}/{d} + {b}/{d} = ___（最简分数或小数）", {"a": "int:1-6", "b": "int:1-6", "d": "choice:3,4,6,8"}, "(a+b)/d", None, ["分子相加", "约分"]),
            ("dec_mult", "0.{b} × 100 = ___", {"b": "int:1-9"}, "b*10+b", None, ["小数点移动"]),
            ("frac_mult", "{a} × {b}/{d} = ___", {"a": "int:2-5", "b": "int:2-5", "d": "choice:2,4,5,8"}, "a*b/d", None, ["整数乘分数"]),
            ("simple_eq", "2x = {a}，x = ___", {"a": "int:10-40"}, "a/2", None, ["两边同除以2"]),
        ],
        ("easy", "constructed"): [
            ("frac_add_same", "计算 {a}/{d} + {b}/{d}，写出计算过程与结果。", {"a": "int:1-5", "b": "int:1-5", "d": "choice:4,6,8,10"}, "(a+b)/d", None, ["同分母", "相加", "化简"]),
            ("dec_mult", "计算 {a}.{b} × {c}，说明小数点位置。", {"a": "int:1-9", "b": "int:1-9", "c": "int:2-9"}, "(a*10+b)*c/10", None, ["按整数乘", "点小数点"]),
        ],
        ("medium", "choice"): [
            ("frac_mult", "一瓶果汁喝去{a}/{d}，还剩几分之几？", {"a": "int:1-5", "d": "choice:4,5,6,8"}, "(d-a)/d", ["{ans}", "{a}/{d}", "1/{d}", "{a}"], ["单位1", "减法"]),
            ("dec_mult", "{a}.{b} × {c}.{d} 的积有几位小数？", {"a": "int:1-3", "b": "int:1-9", "c": "int:1-3", "d": "int:1-9"}, "2", ["2", "1", "3", "4"], ["数位和"]),
            ("simple_eq", "3x - {a} = {b}，x = ?", {"a": "int:1-15", "b": "int:16-45"}, "(b+a)/3", ["{ans}", "{b-a}", "{b}", "{a}"], ["移项", "除以3"]),
        ],
        ("medium", "fill"): [
            ("frac_add_same", "{a}/{d} + {b}/{d} = {c}/{d}，c = ___", {"a": "int:2-7", "b": "int:2-7", "d": "choice:6,8,10,12"}, "a+b", None, ["分子相加"]),
            ("dec_mult", "{a} ÷ 100 = ___", {"a": "int:1-9"}, "a/100", None, ["除以100"]),
            ("simple_eq", "x ÷ {a} = {b}，x = ___", {"a": "int:2-9", "b": "int:2-12"}, "a*b", None, ["逆运算"]),
        ],
        ("medium", "constructed"): [
            ("frac_mult", "整块地面积的{a}/{d}种白菜，种萝卜是白菜的{b}倍，种萝卜占几分之几？", {"a": "int:1-3", "b": "int:2-4", "d": "choice:4,5,6,8"}, "a*b/d", None, ["求白菜占比", "乘倍数", "化简"]),
            ("simple_eq", "一个数的{a}倍是{b}，列方程并求解。", {"a": "int:2-8", "b": "int:10-48"}, "b/a", None, ["设未知数", "列方程", "求解"]),
        ],
        ("hard", "choice"): [
            ("frac_add_same", "计算：{a}/{d} + {b}/{d} + {c}/{d} = ?", {"a": "int:1-4", "b": "int:1-4", "c": "int:1-4", "d": "choice:6,8,10,12"}, "(a+b+c)/d", ["{ans}", "{a+b+c}", "{d}", "1"], ["同分母相加", "化简"]),
        ],
        ("hard", "fill"): [
            ("dec_mult", "1.{b} × 1.{d} = ___（保留两位小数）", {"b": "int:10-99", "d": "int:10-99"}, "round((100+b)*(100+d)/10000, 2)", None, ["整数化", "相乘", "还原"]),
        ],
    },
    6: {
        ("easy", "choice"): [
            ("ratio", "男生{a}人，女生{b}人，男生与女生人数比是？", {"a": "int:10-30", "b": "int:10-30"}, "a/b", ["{a}:{b}", "{b}:{a}", "{a+b}", "{a-b}"], ["比的前项后项"]),
            ("percent", "{a}的{b}%是多少？", {"a": "int:100-400", "b": "choice:10,20,25,50"}, "a*b/100", ["{ans}", "{a}", "{b}", "{a+b}"], ["百分数化小数", "相乘"]),
            ("frac_div", "计算：{a}/{d} ÷ {b} = ?", {"a": "int:1-6", "b": "int:2-5", "d": "choice:2,4,5,8"}, "a/(d*b)", ["{ans}", "{a}/{b}", "{a*b}", "{d}"], ["除以整数", "化简"]),
            ("circle_area", "半径{r}cm的圆，π取3.14，面积约为？", {"r": "int:2-5"}, "round(3.14*r*r, 2)", ["{ans}", "{r*2}", "{r*3.14}", "6.28"], ["S=πr²", "代入"]),
        ],
        ("easy", "fill"): [
            ("ratio", "化简比 {a}:{b} = ___:1", {"a": "int:10-50", "b": "choice:2,5,10"}, "a/b", None, ["同时除以b"]),
            ("percent", "0.{b} = ___%", {"b": "int:1-9"}, "b*10", None, ["小数化百分数"]),
            ("frac_div", "{a}/{d} ÷ 2 = ___", {"a": "int:2-8", "d": "choice:4,6,8,10"}, "a/(2*d)", None, ["除以2"]),
            ("factors", "{a}和{b}的最大公因数是___", {"a": "int:12-36", "b": "int:8-24"}, "gcd(a,b)", None, ["列举因数"]),
        ],
        ("easy", "constructed"): [
            ("ratio", "糖与水的质量比是{a}:{b}，若糖{a}g，求水多少克。", {"a": "int:2-5", "b": "int:3-8"}, "b", None, ["写比", "按比例", "计算"]),
            ("circle_area", "半径{r}cm，π=3.14，写出圆面积公式并计算。", {"r": "int:3-6"}, "round(3.14*r*r, 2)", None, ["公式", "代入", "得数"]),
        ],
        ("medium", "choice"): [
            ("percent", "原价{a}元，打{b}折后售价多少元？", {"a": "int:100-500", "b": "choice:80,85,90,95"}, "a*b/100", ["{ans}", "{a}", "{b}", "{a-b}"], ["折扣即百分数", "相乘"]),
            ("frac_div", "{a}/{d} ÷ {e}/{f} = ?", {"a": "int:1-4", "d": "int:2-6", "e": "int:1-4", "f": "int:2-6"}, "a*f/(d*e)", ["{ans}", "{a}/{d}", "{e}/{f}", "1"], ["除法变乘法", "约分"]),
            ("circle_area", "直径{d}cm的圆，π=3.14，面积约？", {"d": "int:4-10"}, "round(3.14*(d/2)*(d/2), 2)", ["{ans}", "{d*3.14}", "{d}", "3.14"], ["先求半径", "S=πr²"]),
        ],
        ("medium", "fill"): [
            ("ratio", "地图比例尺1:{s}，图上{a}cm表示实际___cm。", {"s": "choice:1000,5000,10000", "a": "int:2-8"}, "a*s", None, ["比例尺含义"]),
            ("percent", "某班{a}人，优秀率{b}%，优秀约___人", {"a": "int:30-50", "b": "choice:20,25,30,40"}, "round(a*b/100)", None, ["百分数乘总数"]),
            ("frac_div", "一个数的 {a}/{d} 是 {n}，这个数是___", {"a": "int:1-3", "d": "int:2-6", "n": "int:4-24"}, "n*d/a", None, ["单位1", "逆运算"]),
        ],
        ("medium", "constructed"): [
            ("percent", "进价{a}元，按{b}%利润定价，求售价。", {"a": "int:50-200", "b": "choice:10,20,25,30"}, "a*(100+b)/100", None, ["利润含义", "列式", "计算"]),
            ("factors", "求{a}和{b}的最小公倍数。", {"a": "int:12-24", "b": "int:18-36"}, "lcm(a,b)", None, ["短除", "乘除积"]),
        ],
        ("hard", "choice"): [
            ("frac_div", "甲数比乙数多{a}%，乙数是{b}，甲数是多少？", {"a": "choice:10,20,25,30", "b": "int:80-200"}, "b*(100+a)/100", ["{ans}", "{b}", "{a}", "{b+a}"], ["单位1", "百分数应用"]),
        ],
        ("hard", "fill"): [
            ("circle_area", "外半径{R}cm、内半径{r}cm，π=3.14，圆环面积约___", {"R": "int:5-8", "r": "int:2-4"}, "round(3.14*(R*R-r*r), 2)", None, ["大圆减小圆"]),
        ],
    },
}


def _build_templates() -> list[dict]:
    templates: list[dict] = []
    for grade in (4, 5, 6):
        idx = 0
        for diff, item_type, count in MIX:
            if count == 0:
                continue
            pool = STEMS[grade][(diff, item_type)]
            for i in range(count):
                kid, stem, slots, expr, choices, rubric = pool[i % len(pool)]
                idx += 1
                row = {
                    "id": f"g{grade}_{diff}_{item_type}_{idx:02d}",
                    "grades": [grade],
                    "item_type": item_type,
                    "difficulty": diff,
                    "knowledge_ids": [kid],
                    "stem_template": stem,
                    "slots": slots,
                    "answer_expr": expr,
                    "rubric_steps": rubric or [],
                }
                if choices:
                    row["choices_template"] = choices
                templates.append(row)
    return templates


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    templates = _build_templates()
    (OUT / "knowledge.json").write_text(
        json.dumps(KNOWLEDGE, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "templates.json").write_text(
        json.dumps(templates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(KNOWLEDGE)} knowledge nodes, {len(templates)} templates")


if __name__ == "__main__":
    main()
