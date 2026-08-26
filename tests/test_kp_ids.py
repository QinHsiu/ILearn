# tests/test_kp_ids.py
from pathlib import Path
import json
from ilearn.data.kp_ids import slugify_kp, resolve_kp_id, load_alias_map

def test_slugify_kp_ascii():
    assert slugify_kp("三位数乘两位数") == "mult_3digit"  # via alias
    assert slugify_kp("Hello World!") == "hello_world"

def test_resolve_legacy_alias():
    alias = {"三位数乘两位数": "mult_3digit", "mult_3digit": "mult_3digit"}
    assert resolve_kp_id("三位数乘两位数", alias) == "mult_3digit"
    assert resolve_kp_id("mult_3digit", alias) == "mult_3digit"
    assert resolve_kp_id("未知知识点", alias) is None

def test_load_alias_map_from_repo():
    root = Path(__file__).resolve().parents[1]
    m = load_alias_map(root / "data" / "curriculum" / "kp_alias.json")
    assert m["三位数乘两位数"] == "mult_3digit"
    assert m["同分母分数加法"] == "frac_add_same"
