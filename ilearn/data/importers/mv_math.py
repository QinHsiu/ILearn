"""Import MV-MATH records into curriculum-bound multimodal bank items."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BINDINGS = REPO_ROOT / "data" / "curriculum" / "mv_math_bindings.json"
DEFAULT_OVERRIDES = REPO_ROOT / "data" / "curriculum" / "chapter_overrides.json"

REGION = "北京"
EDITION = "人教版"
SOURCE_LABEL = "北京·人教·小学数学"

_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_NUMERIC_ANSWER_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?|\d+/\d+)")
_LATEX_STRIP_RE = re.compile(r"[\$\\{}]|\\[a-zA-Z]+")
_DIFF_BUCKETS = ("easy", "medium", "hard")


def load_bindings(path: str | Path | None = None) -> dict:
    bindings_path = Path(path) if path is not None else DEFAULT_BINDINGS
    with bindings_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_mv_math_records(path: Path) -> Iterator[dict]:
    """Yield records from a JSON array file or JSONL."""
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        records = json.loads(text)
        for record in records:
            yield record
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _grade_key(grade: int) -> str:
    return f"{grade}年级"


def _allowed_mv_grades(bindings: dict) -> set[str]:
    grade_map = bindings.get("grade_map", {})
    allowed: set[str] = set()
    for mv_grade, pilot_grades in grade_map.items():
        if pilot_grades:
            allowed.add(mv_grade)
    return allowed


def resolve_binding(record: dict, rules: list[dict], bindings: dict | None = None) -> dict | None:
    """Return bind dict for the first matching rule, or None if unmatched."""
    if bindings is not None:
        allowed = _allowed_mv_grades(bindings)
        mv_grade = str(record.get("grade", "")).strip()
        if allowed and mv_grade not in allowed:
            return None

    question = str(record.get("question") or "").strip()
    subject = str(record.get("subject") or "").strip()

    for rule in rules:
        match = rule.get("match", {})
        expected_subject = match.get("mv_subject")
        if expected_subject and subject != expected_subject:
            continue
        pattern = match.get("stem_regex")
        if pattern and not re.search(pattern, question, re.I):
            continue
        bind = rule.get("bind")
        if bind:
            return dict(bind)
    return None


def _chapter_weeks(
    overrides: dict,
    grade: int,
    semester: str,
    chapter: str,
) -> list[int]:
    chapters = (
        overrides.get(REGION, {})
        .get(EDITION, {})
        .get(_grade_key(grade), {})
        .get(semester, {})
        .get("chapters", [])
    )
    for block in chapters:
        if block.get("chapter") == chapter:
            return list(block.get("weeks", []))
    return []


def _normalize_difficulty(value: object, *, problem_id: str = "") -> str:
    if value is not None:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"low", "easy", "simple"}:
                return "easy"
            if lowered in {"high", "hard", "difficult"}:
                return "hard"
            if lowered in {"medium", "mid"}:
                return "medium"
        if isinstance(value, (int, float)):
            if value <= 2:
                return "easy"
            if value >= 4:
                return "hard"
            return "medium"
    if problem_id:
        return _DIFF_BUCKETS[hash(problem_id) % len(_DIFF_BUCKETS)]
    return "medium"


def _parse_answer(answer: object, answer_type: str) -> str | None:
    if answer is None:
        return None
    text = str(answer).strip()
    if not text:
        return None
    if answer_type == "choice":
        letter = re.match(r"^[A-Da-d]$", text)
        if letter:
            return text.upper()
    cleaned = _LATEX_STRIP_RE.sub("", text).strip().rstrip(".°")
    match = _NUMERIC_ANSWER_RE.match(cleaned)
    if match:
        return match.group(1)
    digit = re.search(r"(-?\d+(?:\.\d+)?|\d+/\d+)", cleaned)
    if digit:
        return digit.group(1)
    if answer_type == "choice":
        return text.upper()[:1]
    return None


def _is_english_stem(text: str) -> bool:
    return bool(text.strip()) and not _CHINESE_RE.search(text)


def _pick_chinese_stem(
    knowledge_id: str,
    example_bank: dict[str, list[dict]],
    problem_id: str,
) -> str | None:
    examples = example_bank.get(knowledge_id, [])
    chinese = [
        ex for ex in examples
        if _CHINESE_RE.search(str(ex.get("stem") or ""))
    ]
    if not chinese:
        return None
    idx = hash(problem_id) % len(chinese)
    return str(chinese[idx]["stem"]).strip()


def _item_id(problem_id: str) -> str:
    safe = re.sub(r"[^\w-]", "_", problem_id).strip("_")
    if len(safe) > 48:
        safe = safe[:48]
    return f"mmv-{safe}"


def extract_images(
    record: dict,
    raw_mv_dir: Path,
    pilot_dir: Path,
    item_id: str,
) -> list[str]:
    """Copy MV-MATH images into pilot assets; return paths relative to pilot_dir."""
    problem_id = str(record.get("problem_id") or "").strip()
    if not problem_id:
        return []

    assets_dir = pilot_dir / "assets" / "mv_math" / item_id
    rel_prefix = f"assets/mv_math/{item_id}"
    rel_paths: list[str] = []

    recorded = record.get("input_image_paths") or []
    if recorded:
        for index, rel in enumerate(recorded):
            rel_path = Path(str(rel))
            candidates = [
                raw_mv_dir / rel_path,
                raw_mv_dir / "images" / problem_id / rel_path.name,
            ]
            src = next((path for path in candidates if path.is_file()), None)
            if src is None:
                continue
            assets_dir.mkdir(parents=True, exist_ok=True)
            dest = assets_dir / f"{index}.png"
            shutil.copy2(src, dest)
            rel_paths.append(f"{rel_prefix}/{index}.png")
        if rel_paths:
            return rel_paths

    image_dir = raw_mv_dir / "images" / problem_id
    if not image_dir.is_dir():
        return []

    assets_dir.mkdir(parents=True, exist_ok=True)
    for index, src in enumerate(sorted(path for path in image_dir.iterdir() if path.is_file())):
        dest = assets_dir / f"{index}{src.suffix or '.png'}"
        shutil.copy2(src, dest)
        rel_paths.append(f"{rel_prefix}/{dest.name}")
    return rel_paths


def _image_relevance(value: object) -> str:
    text = str(value or "0").strip()
    if text in {"1", "mutually_dependent", "dependent"}:
        return "mutually_dependent"
    return "independent"


def to_multimodal_item(
    record: dict,
    bind: dict,
    image_paths: list[str],
    example_bank: dict[str, list[dict]],
    *,
    overrides_path: str | Path | None = None,
) -> dict | None:
    """Build a multimodal bank item with nested curriculum_ref."""
    overrides_path = Path(overrides_path) if overrides_path is not None else DEFAULT_OVERRIDES
    with overrides_path.open(encoding="utf-8") as handle:
        overrides = json.load(handle)

    problem_id = str(record.get("problem_id") or "").strip()
    if not problem_id:
        return None

    knowledge_ids = list(bind.get("knowledge_ids") or [])
    if not knowledge_ids:
        return None

    grade = bind.get("grade")
    semester = bind.get("semester")
    chapter = bind.get("chapter")
    objective_ids = list(bind.get("objective_ids") or [])
    if grade is None or not semester or not chapter or not objective_ids:
        return None

    weeks = _chapter_weeks(overrides, int(grade), semester, chapter)
    if not weeks:
        return None

    answer_type = str(record.get("answer_type") or "free-form").strip().lower()
    answer = _parse_answer(record.get("answer"), answer_type)
    if answer is None:
        return None

    question = str(record.get("question") or "").strip()
    stem = question
    if _is_english_stem(question) or answer_type == "choice":
        donor = _pick_chinese_stem(knowledge_ids[0], example_bank, problem_id)
        if donor:
            stem = donor
    if not stem:
        return None

    item_id = _item_id(problem_id)
    curriculum_ref = {
        "region": REGION,
        "edition": EDITION,
        "grade": grade,
        "semester": semester,
        "chapter": chapter,
        "weeks": weeks,
        "objective_ids": objective_ids,
        "source_label": SOURCE_LABEL,
    }

    item: dict = {
        "id": item_id,
        "stem": stem,
        "answer": answer,
        "answer_type": answer_type if answer_type in {"choice", "free-form", "multi-step"} else "free-form",
        "difficulty": _normalize_difficulty(record.get("difficulty"), problem_id=problem_id),
        "knowledge_ids": knowledge_ids,
        "image_paths": list(image_paths),
        "image_relevance": _image_relevance(record.get("image_relavance")),
        "curriculum_ref": curriculum_ref,
        "source": "mv_math",
        "source_problem_id": problem_id,
    }

    analysis = record.get("analysis")
    if analysis:
        item["analysis"] = str(analysis).strip()

    return item
