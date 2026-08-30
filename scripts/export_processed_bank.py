"""Export cleaned open-dataset items into data/processed/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ilearn.data.importers.mm_k12 import iter_mm_k12_records, to_example_entry
from ilearn.data.importers.tal_scq5k import to_example_from_scq5k
from ilearn.data.kp_ids import load_alias_map


def _alias_map() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    alias_path = root / "data" / "curriculum" / "kp_alias.json"
    if alias_path.exists():
        return load_alias_map(alias_path)
    return {}


def _normalized_from_example(
    knowledge_id: str, example: dict[str, Any], *, source: str
) -> dict[str, Any]:
    return {
        "id": example["id"],
        "stem": example["stem"],
        "type": "fill",
        "options": example.get("choices") or [],
        "correct_answer": example.get("answer") or example.get("correct_answer") or "",
        "difficulty": example.get("difficulty", "medium"),
        "grade": example.get("grade") or 4,
        "skill_id": knowledge_id,
        "source": source,
    }


def export_mm_k12(raw_path: Path, output_path: Path) -> int:
    alias = _alias_map()
    questions: list[dict[str, Any]] = []
    if raw_path.suffix.lower() == ".json":
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("data", [])
        for item in records:
            mapped = to_example_entry(item, alias)
            if mapped is None:
                continue
            kp, example = mapped
            questions.append(_normalized_from_example(kp, example, source="mm_k12"))
    else:
        for item in iter_mm_k12_records(raw_path):
            mapped = to_example_entry(item, alias)
            if mapped is None:
                continue
            kp, example = mapped
            questions.append(_normalized_from_example(kp, example, source="mm_k12"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(questions)


def export_tal_scq5k(raw_path: Path, output_path: Path) -> int:
    alias = _alias_map()
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("data", [])
    questions: list[dict[str, Any]] = []
    for item in records:
        mapped = to_example_from_scq5k(item, alias, hard_only=False)
        if mapped is None:
            continue
        kp, example = mapped
        questions.append(_normalized_from_example(kp, example, source="tal_scq5k"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(questions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export cleaned dataset bank")
    parser.add_argument("--source", choices=("mm_k12", "tal_scq5k"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"missing input: {args.input}", file=sys.stderr)
        return 1
    if args.source == "mm_k12":
        count = export_mm_k12(args.input, args.output)
    else:
        count = export_tal_scq5k(args.input, args.output)
    print(f"wrote {count} items -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
