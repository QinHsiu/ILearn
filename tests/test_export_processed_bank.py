"""Tests for processed bank export."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "mm_k12_tiny.jsonl"
ROOT = Path(__file__).resolve().parents[1]


def _load_export_module():
    path = ROOT / "scripts" / "export_processed_bank.py"
    spec = importlib.util.spec_from_file_location("export_processed_bank", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_export_mm_k12_writes_cleaned_items(tmp_path: Path):
    mod = _load_export_module()
    out = tmp_path / "mm_k12_cleaned.json"
    count = mod.export_mm_k12(FIX, out)
    assert count >= 1
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["source"] == "mm_k12"
    assert data[0]["skill_id"]
    assert data[0]["stem"]
