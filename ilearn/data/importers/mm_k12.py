from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ilearn.data.kp_ids import resolve_kp_id

DEFAULT_LABEL = "北京·人教·小学数学"
PILOT_GRADES = frozenset({4, 5, 6})

_GRADE_CHAPTER = {
    4: "四年级上册",
    5: "五年级上册",
    6: "六年级上册",
}

_TOPIC_FIELDS = ("topic", "knowledge", "knowledge_point", "知识点")
_DIFF_BUCKETS = ("easy", "medium", "hard")
_NUMERIC_ANSWER_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?|\d+/\d+)")
_LATEX_STRIP_RE = re.compile(r"[\$\\{}]|\\[a-zA-Z]+")

# English keyword heuristics (MM-K12 is mostly English geometry/algebra).
_ENGLISH_KP_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rectangle|rectangular", re.I), "rect_area"),
    (re.compile(r"circle.{0,40}area|area.{0,40}circle|radius.{0,30}area", re.I), "circle_area"),
    (re.compile(r"parallel|perpendicular", re.I), "parallel_perp"),
    (re.compile(r"\bangle\b|degrees?|°", re.I), "angle_measure"),
    (re.compile(r"percent|% of", re.I), "percent"),
    (re.compile(r"\bratio\b|proportion", re.I), "ratio"),
    (re.compile(r"factor|multiple|lcm|gcf|divisor", re.I), "factors"),
    (re.compile(r"\bequation\b|solve for \w+", re.I), "simple_eq"),
    (re.compile(r"decimal.{0,30}mult|multip.{0,30}decimal", re.I), "dec_mult"),
    (re.compile(r"fraction.{0,30}div|divide.{0,30}fraction", re.I), "frac_div"),
    (re.compile(r"fraction.{0,30}(mult|times|product)|multip.{0,30}fraction", re.I), "frac_mult"),
    (re.compile(r"fraction.{0,30}add|add.{0,30}fraction|same denominator", re.I), "frac_add_same"),
    (re.compile(r"three.?digit|multipl.{0,30}digit|\d{2,3}\s*[×x*]\s*\d{2,3}", re.I), "mult_3digit"),
    (re.compile(r"\barea\b", re.I), "rect_area"),
]


def iter_mm_k12_records(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _parse_grade(record: dict) -> int | None:
    for key in ("grade", "年级"):
        if key not in record:
            continue
        value = record[key]
        if isinstance(value, str):
            match = re.search(r"(\d+)", value)
            if match:
                return int(match.group(1))
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _normalize_difficulty(value: object, *, record_id: str = "") -> str:
    if value is not None:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"easy", "simple", "简单"}:
                return "easy"
            if lowered in {"hard", "difficult", "困难"}:
                return "hard"
            if lowered in {"medium", "中等"}:
                return "medium"
            try:
                value = int(lowered)
            except ValueError:
                return "medium"
        if isinstance(value, (int, float)):
            if value <= 2:
                return "easy"
            if value >= 4:
                return "hard"
            return "medium"
    if record_id:
        return _DIFF_BUCKETS[hash(record_id) % len(_DIFF_BUCKETS)]
    return "medium"


def _parse_numeric_answer(answer: object) -> str | None:
    if answer is None:
        return None
    text = str(answer).strip()
    if not text:
        return None
    cleaned = _LATEX_STRIP_RE.sub("", text).strip().rstrip(".°")
    match = _NUMERIC_ANSWER_RE.match(cleaned)
    if match:
        return match.group(1)
    digit = re.search(r"(-?\d+(?:\.\d+)?|\d+/\d+)", cleaned)
    if digit:
        return digit.group(1)
    return None


def _question_text(record: dict) -> str:
    return str(record.get("question") or record.get("stem") or "").strip()


def _match_english_keywords(question: str) -> str | None:
    for pattern, kp_id in _ENGLISH_KP_RULES:
        if pattern.search(question):
            return kp_id
    return None


def _match_knowledge_id(record: dict, alias_map: dict[str, str]) -> str | None:
    for key in _TOPIC_FIELDS:
        if key not in record:
            continue
        kp_id = resolve_kp_id(str(record[key]).strip(), alias_map)
        if kp_id:
            return kp_id

    question = _question_text(record)
    labels = sorted(
        (label for label in alias_map if label and not label.isascii()),
        key=len,
        reverse=True,
    )
    for label in labels:
        if label in question:
            return alias_map[label]

    return _match_english_keywords(question)


def _knowledge_label(knowledge_id: str, alias_map: dict[str, str]) -> str:
    for label, kp_id in alias_map.items():
        if kp_id == knowledge_id and label and not label.isascii():
            return label
    return knowledge_id


def _chapter_for(knowledge_id: str, grade: int | None, alias_map: dict[str, str]) -> str:
    label = _knowledge_label(knowledge_id, alias_map)
    if grade in _GRADE_CHAPTER:
        return f"{_GRADE_CHAPTER[grade]} {label}"
    return label


def _example_id(record: dict) -> str:
    raw_id = str(record.get("id", "")).strip()
    if raw_id.startswith("ex-mm-"):
        return raw_id
    suffix = raw_id or "unknown"
    return f"ex-mm-{suffix}"


def to_example_entry(record: dict, alias_map: dict[str, str]) -> tuple[str, dict] | None:
    grade = _parse_grade(record)
    if grade is not None and grade not in PILOT_GRADES:
        return None

    knowledge_id = _match_knowledge_id(record, alias_map)
    if knowledge_id is None:
        return None

    answer = _parse_numeric_answer(record.get("answer"))
    if answer is None:
        return None

    stem = _question_text(record)
    if not stem:
        return None

    example = {
        "id": _example_id(record),
        "stem": stem,
        "chapter": _chapter_for(knowledge_id, grade, alias_map),
        "label": DEFAULT_LABEL,
        "answer": answer,
        "difficulty": _normalize_difficulty(record.get("difficulty"), record_id=str(record.get("id", ""))),
        "source": "mm_k12",
    }
    return knowledge_id, example
