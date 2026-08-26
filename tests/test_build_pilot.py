import json
import shutil
from pathlib import Path

from ilearn.data.build_pilot import build_pilot

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[1]
ALIAS = REPO_ROOT / "data" / "curriculum" / "kp_alias.json"


def _setup_raw(raw: Path) -> None:
    rcae_dir = raw / "rcae"
    rcae_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES / "rcae_tiny.json",
        rcae_dir / "china_primary_school_math_knowledge_graph.json",
    )

    mm_dir = raw / "mm_k12"
    mm_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "mm_k12_tiny.jsonl", mm_dir / "items.jsonl")

    tal_dir = raw / "tal_scq5k"
    tal_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "tal_scq5k_tiny.jsonl", tal_dir / "items.jsonl")


def test_build_pilot_from_fixtures(tmp_path: Path):
    raw = tmp_path / "raw"
    _setup_raw(raw)
    pilot = tmp_path / "pilot"
    graph = tmp_path / "knowledge_graph.json"
    progress = tmp_path / "progress_mapping.json"

    report = build_pilot(raw, pilot, graph, progress, ALIAS)

    assert report.knowledge_count >= 13
    assert (pilot / "knowledge.json").is_file()
    assert (pilot / "example_bank.json").is_file()
    assert graph.is_file()
    assert progress.is_file()

    bank = json.loads((pilot / "example_bank.json").read_text(encoding="utf-8"))
    assert bank
    assert sum(len(items) for items in bank.values()) >= 1
