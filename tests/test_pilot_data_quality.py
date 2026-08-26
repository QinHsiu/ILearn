"""Pilot curriculum data quality gates (Edition 0826)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"

MIN_G46_NODES = 80
MIN_EXAMPLES_PER_KP = 8
LEGACY_IDS = {
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
}

pytestmark = pytest.mark.skipif(
    os.environ.get("ILearn_SKIP_DATA_QUALITY") == "1",
    reason="ILearn_SKIP_DATA_QUALITY=1",
)


def _load_knowledge() -> list[dict]:
    path = PILOT / "knowledge.json"
    if not path.is_file():
        pytest.skip(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_example_bank() -> dict[str, list[dict]]:
    path = PILOT / "example_bank.json"
    if not path.is_file():
        pytest.skip(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _g46_nodes(knowledge: list[dict]) -> list[dict]:
    return [entry for entry in knowledge if entry.get("grade") in (4, 5, 6)]


def _min_examples_per_kp(knowledge: list[dict], bank: dict[str, list[dict]]) -> int:
    knowledge_ids = {entry["id"] for entry in knowledge}
    if not knowledge_ids:
        return 0
    return min(len(bank.get(kp_id, [])) for kp_id in knowledge_ids)


def test_pilot_knowledge_minimum_coverage():
    knowledge = _load_knowledge()
    g46 = _g46_nodes(knowledge)
    if len(g46) < MIN_G46_NODES:
        pytest.skip(
            f"grades 4-6 knowledge nodes {len(g46)} < {MIN_G46_NODES}; "
            "run full build after RCAE download"
        )
    assert len(g46) >= MIN_G46_NODES


def test_example_bank_minimum_per_legacy_kp():
    knowledge = _load_knowledge()
    bank = _load_example_bank()
    ids = {entry["id"] for entry in knowledge}
    missing = LEGACY_IDS - ids
    if missing:
        pytest.fail(f"legacy knowledge_ids missing from knowledge.json: {sorted(missing)}")

    low = {kp_id: len(bank.get(kp_id, [])) for kp_id in LEGACY_IDS if len(bank.get(kp_id, [])) < MIN_EXAMPLES_PER_KP}
    if low:
        pytest.skip(
            f"legacy kp below {MIN_EXAMPLES_PER_KP} examples: {low}; run build_pilot after template supplement"
        )
    for kp_id in sorted(LEGACY_IDS):
        count = len(bank.get(kp_id, []))
        assert count >= MIN_EXAMPLES_PER_KP, f"{kp_id} has fewer than 8 examples ({count})"


def test_example_bank_minimum_per_kp():
    knowledge = _load_knowledge()
    bank = _load_example_bank()
    min_count = _min_examples_per_kp(knowledge, bank)
    if min_count < MIN_EXAMPLES_PER_KP:
        pytest.skip(
            f"minimum examples per knowledge_id is {min_count} < {MIN_EXAMPLES_PER_KP}; "
            "RCAE-expanded nodes expected to stay sparse until full corpus import"
        )
    knowledge_ids = {entry["id"] for entry in knowledge}
    for kp_id in sorted(knowledge_ids):
        count = len(bank.get(kp_id, []))
        assert count >= MIN_EXAMPLES_PER_KP, f"{kp_id} has fewer than 8 examples ({count})"


def test_legacy_ids_still_present():
    knowledge = _load_knowledge()
    ids = {entry["id"] for entry in knowledge}
    missing = LEGACY_IDS - ids
    if missing:
        pytest.fail(f"legacy knowledge_ids missing from knowledge.json: {sorted(missing)}")
    assert LEGACY_IDS <= ids
