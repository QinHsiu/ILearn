from __future__ import annotations

import hashlib
import re

from ilearn.data.kp_ids import resolve_kp_id

DEFAULT_LABEL = "北京·人教·小学数学"
STEM_HASH_PREFIX_LEN = 12
_ROUTE_SEP = "->"

_LEGACY_KP_IDS = frozenset({
    "mult_3digit",
    "rect_area",
    "angle_measure",
    "parallel_perp",
    "dec_mult",
    "frac_add_same",
    "frac_mult",
    "simple_eq",
    "frac_div",
    "ratio",
    "circle_area",
    "percent",
    "factors",
})

# TAL route / stem keywords → legacy pilot knowledge_id (中文竞赛题标签与课内 kp 对齐).
_ROUTE_KP_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"分数乘法|分数乘分数|分数乘法运算"), "frac_mult"),
    (re.compile(r"分数除法|分数除|分数除法运算"), "frac_div"),
    (re.compile(r"同分母分数|分数加法|分数加减|分数加法运算"), "frac_add_same"),
    (re.compile(r"三位数乘两位数|整数乘法.*三位|三位数.*乘"), "mult_3digit"),
    (re.compile(r"小数乘法|小数乘除|小数乘法运算"), "dec_mult"),
    (re.compile(r"简易方程|列方程解应用题|一元一次方程"), "simple_eq"),
    (re.compile(r"比和比例|比例应用|按比例"), "ratio"),
    (re.compile(r"百分数|百分"), "percent"),
    (re.compile(r"因数与倍数|因数|倍数|公因数|公倍数"), "factors"),
    (re.compile(r"长方形面积|平行四边形面积|多边形面积"), "rect_area"),
    (re.compile(r"圆的面积|圆面积"), "circle_area"),
    (re.compile(r"平行与垂直|平行四边形|梯形"), "parallel_perp"),
    (re.compile(r"角的度量|角度|用量角"), "angle_measure"),
]


def stem_hash_prefix(stem: str) -> str:
    normalized = stem.strip()
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return digest[:STEM_HASH_PREFIX_LEN]


def extract_kp_routes(record: dict) -> list[str]:
    routes = record.get("knowledge_point_routes") or []
    return [str(route).strip() for route in routes if str(route).strip()]


def _question_text(record: dict) -> str:
    return str(record.get("question") or record.get("problem") or "").strip()


def _answer_text(record: dict) -> str:
    for key in ("answer", "answer_value"):
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _route_labels(route: str) -> list[str]:
    return [part.strip() for part in route.split(_ROUTE_SEP) if part.strip()]


def _is_hard_difficulty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"hard", "difficult", "困难"}:
            return True
        try:
            value = int(lowered)
        except ValueError:
            return False
    if isinstance(value, (int, float)):
        return int(value) >= 3
    return False


def _normalize_tal_difficulty(value: object, *, record_id: str = "") -> str:
    if _is_hard_difficulty(value):
        return "hard"
    if value is not None:
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                return "medium"
        if isinstance(value, (int, float)):
            if int(value) <= 1:
                return "easy"
            if int(value) == 2:
                return "medium"
    if record_id:
        buckets = ("easy", "medium", "hard")
        return buckets[hash(record_id) % len(buckets)]
    return "medium"


def _match_route_keywords(record: dict) -> str | None:
    blob = " ".join(extract_kp_routes(record)) + " " + _question_text(record)
    for pattern, kp_id in _ROUTE_KP_RULES:
        if pattern.search(blob):
            return kp_id
    return None


def _match_knowledge_id(record: dict, alias_map: dict[str, str]) -> str | None:
    """Prefer legacy pilot kp ids; avoid matching unrelated RCAE node names."""
    keyword_match = _match_route_keywords(record)
    if keyword_match:
        return keyword_match

    blob = _question_text(record) + " " + " ".join(extract_kp_routes(record))
    legacy_labels = sorted(
        (label for label, kp_id in alias_map.items() if kp_id in _LEGACY_KP_IDS and label and not label.isascii()),
        key=len,
        reverse=True,
    )
    for label in legacy_labels:
        if label in blob:
            return alias_map[label]

    for route in extract_kp_routes(record):
        for label in reversed(_route_labels(route)):
            kp_id = resolve_kp_id(label, alias_map)
            if kp_id and kp_id in _LEGACY_KP_IDS:
                return kp_id

    return None


def _knowledge_label(knowledge_id: str, alias_map: dict[str, str]) -> str:
    for label, kp_id in alias_map.items():
        if kp_id == knowledge_id and label and not label.isascii():
            return label
    return knowledge_id


def _example_id(record: dict) -> str:
    raw_id = str(record.get("id") or record.get("qid") or record.get("queId") or "").strip()
    if raw_id.startswith("ex-tal-"):
        return raw_id
    suffix = raw_id or stem_hash_prefix(_question_text(record))
    return f"ex-tal-{suffix}"


def to_example_from_scq5k(
    record: dict,
    alias_map: dict[str, str],
    *,
    hard_only: bool = True,
) -> tuple[str, dict] | None:
    if hard_only and not _is_hard_difficulty(record.get("difficulty")):
        return None

    knowledge_id = _match_knowledge_id(record, alias_map)
    if knowledge_id is None:
        return None

    stem = _question_text(record)
    answer = _answer_text(record)
    if not stem or not answer:
        return None

    record_id = str(record.get("id") or record.get("qid") or record.get("queId") or "")
    difficulty = "hard" if hard_only else _normalize_tal_difficulty(
        record.get("difficulty"), record_id=record_id
    )

    example = {
        "id": _example_id(record),
        "stem": stem,
        "chapter": _knowledge_label(knowledge_id, alias_map),
        "label": DEFAULT_LABEL,
        "answer": answer,
        "difficulty": difficulty,
        "source": "tal_scq5k",
        "kp_routes": extract_kp_routes(record),
        "answer_analysis": list(record.get("answer_analysis") or []),
    }
    return knowledge_id, example
