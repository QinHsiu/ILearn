"""HTTP tests for pilot static asset serving."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "data" / "pilot"


def _minimal_pilot(tmp_path: Path) -> Path:
    pilot = tmp_path / "pilot"
    pilot.mkdir(parents=True)
    for name in ("knowledge.json", "templates.json", "syllabus.json"):
        shutil.copy(PILOT / name, pilot / name)
    return pilot


def _client(tmp_path: Path, pilot_dir: Path) -> TestClient:
    return TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=pilot_dir,
            llm=None,
        )
    )


def test_pilot_assets_serves_image(tmp_path: Path):
    pilot = _minimal_pilot(tmp_path)
    asset = pilot / "assets" / "mv_math" / "demo" / "0.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01")
    client = _client(tmp_path, pilot)
    response = client.get("/pilot-assets/mv_math/demo/0.png")
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_pilot_assets_blocks_traversal(tmp_path: Path):
    pilot = _minimal_pilot(tmp_path)
    (pilot / "secret.txt").write_text("nope", encoding="utf-8")
    client = _client(tmp_path, pilot)
    blocked = client.get("/pilot-assets/mv_math/%2e%2e/secret.txt")
    assert blocked.status_code in (400, 404)
