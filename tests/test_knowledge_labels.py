from ilearn.core.knowledge_labels import (
    looks_like_internal_id,
    resolve_knowledge_label,
    resolve_knowledge_labels,
)


def test_looks_like_internal_id():
    assert looks_like_internal_id("circle_area")
    assert looks_like_internal_id("kp_4433814116")
    assert not looks_like_internal_id("圆的面积")
    assert not looks_like_internal_id("小数乘小数")


def test_resolve_knowledge_label_from_pilot():
    assert resolve_knowledge_label("circle_area") == "圆的面积"
    assert resolve_knowledge_label("dec_mult") == "小数乘法"
    assert resolve_knowledge_label("kp_4433814116") == "小数乘小数"


def test_resolve_knowledge_label_prefers_mastery_name():
    label = resolve_knowledge_label(
        "dec_mult",
        mastery_names={"dec_mult": "小数乘法（单元测评）"},
    )
    assert label == "小数乘法（单元测评）"


def test_resolve_knowledge_labels_dedupes():
    labels = resolve_knowledge_labels(["dec_mult", "dec_mult", "circle_area"])
    assert labels == ["小数乘法", "圆的面积"]
