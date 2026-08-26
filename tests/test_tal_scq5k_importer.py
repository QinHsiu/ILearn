from pathlib import Path
import json

from ilearn.data.importers.tal_scq5k import (
    extract_kp_routes,
    stem_hash_prefix,
    to_example_from_scq5k,
)
from ilearn.data.kp_ids import load_alias_map

FIX = Path(__file__).parent / "fixtures" / "tal_scq5k_tiny.jsonl"
ALIAS = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"


def _load_fixture_rows() -> list[dict]:
    rows = []
    with FIX.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_extract_kp_routes_returns_raw_chains():
    rows = _load_fixture_rows()
    routes = extract_kp_routes(rows[0])
    assert len(routes) == 1
    assert routes[0] == "小学数学->分数->分数乘法->分数乘分数"
    assert "->" in routes[0]


def test_extract_kp_routes_empty_when_missing():
    assert extract_kp_routes({}) == []


def test_to_example_from_scq5k_hard_only():
    alias = load_alias_map(ALIAS)
    rows = _load_fixture_rows()
    mapped = [to_example_from_scq5k(row, alias) for row in rows]
    mapped = [item for item in mapped if item]
    assert len(mapped) == 2


def test_to_example_from_scq5k_maps_knowledge_id():
    alias = load_alias_map(ALIAS)
    rows = _load_fixture_rows()
    kid, ex = to_example_from_scq5k(rows[0], alias)
    assert kid == "frac_mult"
    assert ex["stem"] == rows[0]["question"]
    assert ex["answer"] == "0.4"
    assert ex["source"] == "tal_scq5k"
    assert ex["difficulty"] == "hard"


def test_to_example_from_scq5k_includes_route_metadata():
    alias = load_alias_map(ALIAS)
    rows = _load_fixture_rows()
    _, ex = to_example_from_scq5k(rows[0], alias)
    assert ex["kp_routes"] == rows[0]["knowledge_point_routes"]
    assert ex["answer_analysis"] == rows[0]["answer_analysis"]


def test_stem_hash_prefix_stable_for_dedupe():
    stem = "一根绳子长 3/5 米，用去 2/3，用去多少米？"
    assert stem_hash_prefix(stem) == stem_hash_prefix(stem)
    assert stem_hash_prefix(stem) != stem_hash_prefix("不同题干")


def test_route_keyword_maps_dec_mult():
    alias = load_alias_map(ALIAS)
    record = {
        "qid": "cn-1",
        "problem": "小数乘法：$$0.025\\times 0.04$$的结果的小数位数有位．",
        "answer_value": "B",
        "difficulty": "1",
        "knowledge_point_routes": [
            "知识标签->拓展思维->计算模块->小数->小数乘除->小数乘法运算"
        ],
    }
    mapped = to_example_from_scq5k(record, alias, hard_only=False)
    assert mapped is not None
    assert mapped[0] == "dec_mult"
    assert mapped[1]["source"] == "tal_scq5k"
