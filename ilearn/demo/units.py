"""Load demo unit fixtures from data/demo/units."""

from __future__ import annotations

import json
from pathlib import Path

_UNITS_DIR = Path(__file__).resolve().parents[2] / "data" / "demo" / "units"


def load_demo_unit(unit_id: str) -> dict:
    """Return the JSON fixture for ``unit_id`` or raise FileNotFoundError."""
    trimmed = (unit_id or "").strip()
    if not trimmed or Path(trimmed).name != trimmed:
        raise FileNotFoundError(f"demo unit not found: {unit_id}")
    path = _UNITS_DIR / f"{trimmed}.json"
    if not path.is_file():
        raise FileNotFoundError(f"demo unit not found: {trimmed}")
    return json.loads(path.read_text(encoding="utf-8"))
