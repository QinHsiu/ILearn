from pathlib import Path


VITE_CONFIG = (
    Path(__file__).resolve().parents[1] / "frontend" / "vite.config.ts"
).read_text(encoding="utf-8")


def test_vite_proxies_auth_and_dashboard_to_api_target():
    assert "'/auth':" in VITE_CONFIG
    assert "'/dashboard':" in VITE_CONFIG
    assert VITE_CONFIG.count("target: apiTarget") >= 6
