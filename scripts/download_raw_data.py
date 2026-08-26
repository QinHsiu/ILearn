"""Download helper for Edition 0826 raw curriculum datasets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

INSTRUCTIONS = {
    "rcae": """
RCAE knowledge graph (required):
  curl -L -o data/raw/rcae/china_primary_school_math_knowledge_graph.json \\
    https://raw.githubusercontent.com/digitalboy/RCAE_graph_data/main/china_primary_school_math_knowledge_graph.json
""".strip(),
    "mm_k12": """
MM-K12 (Hugging Face Cierra0506/MM-K12):
  1. pip install datasets
  2. Re-run: python scripts/download_raw_data.py --dataset mm_k12 --download

  Manual export target: data/raw/mm_k12/*.jsonl
""".strip(),
    "tal_scq5k": """
TAL-SCQ5K 中文 (Hugging Face math-eval/TAL-SCQ5K, train split):
  1. pip install datasets
  2. Re-run: python scripts/download_raw_data.py --dataset tal_scq5k --download

  Exports Chinese problems only to data/raw/tal_scq5k/items.jsonl
""".strip(),
}

HF_DATASETS = {
    "mm_k12": ("Cierra0506/MM-K12", "mm_k12", "train"),
    "tal_scq5k": ("math-eval/TAL-SCQ5K", "tal_scq5k", "train"),
}


def _print_instructions(dataset: str) -> None:
    print(INSTRUCTIONS[dataset])


def _serialize_row(row: dict) -> dict:
    record: dict = {}
    for key, value in dict(row).items():
        if key == "image":
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            record[key] = value
        elif isinstance(value, (list, tuple)):
            record[key] = [
                item if isinstance(item, (str, int, float, bool)) or item is None else str(item)
                for item in value
            ]
        else:
            record[key] = str(value)
    return record


def _try_hf_download(dataset: str) -> bool:
    spec = HF_DATASETS.get(dataset)
    if spec is None:
        return False
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets package not installed; showing manual instructions only.", file=sys.stderr)
        return False

    hf_name, subdir, split_name = spec
    out_dir = RAW_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "items.jsonl"

    print(f"Loading {hf_name} [{split_name}] from Hugging Face …")
    loaded = load_dataset(hf_name)
    split = loaded[split_name] if split_name in loaded else loaded.get("train") or next(iter(loaded.values()))
    count = 0
    skipped = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for row in split:
            record = _serialize_row(row)
            if dataset == "tal_scq5k":
                text = str(record.get("problem") or record.get("question") or "")
                if not _CHINESE_RE.search(text):
                    skipped += 1
                    continue
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"Wrote {count} records to {out_path}")
    if dataset == "tal_scq5k" and skipped:
        print(f"Skipped {skipped} non-Chinese records")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download raw curriculum datasets")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=sorted(INSTRUCTIONS),
        help="Dataset to download or show instructions for",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Attempt Hugging Face download (mm_k12, tal_scq5k only)",
    )
    args = parser.parse_args(argv)

    if args.dataset == "rcae":
        _print_instructions("rcae")
        return 0

    if args.download:
        if _try_hf_download(args.dataset):
            return 0

    _print_instructions(args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
