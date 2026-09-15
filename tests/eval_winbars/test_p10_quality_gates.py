"""P10 quality gates visible to users."""

from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.quality_gates_public import quality_gates_payload

PILOT = Path(__file__).resolve().parents[2] / "data" / "pilot"


def test_p10_quality_gates_payload():
    payload = quality_gates_payload()
    assert payload["summary"]["enforced"] >= 3
    assert any(g["id"] == "p3_no_leak" for g in payload["gates"])


def test_p10_quality_gates_endpoint(tmp_path: Path):
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/quality-gates")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total"] == len(body["gates"])
    caps = client.get("/capabilities")
    assert caps.status_code == 200
    assert "quality_gates" in caps.json()


def test_p10_trust_page_mentions_quality_gates():
    root = Path(__file__).resolve().parents[2]
    text = (root / "frontend/src/pages/TrustPage.tsx").read_text(encoding="utf-8")
    assert "quality-gates" in text or "getQualityGates" in text
    assert "质量门" in text
