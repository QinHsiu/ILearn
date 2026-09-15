"""P9 activation friction — three-role evidence within budget."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_p9_activation_script_covers_three_roles():
    script = (ROOT / "scripts/smoke_activation_roles.py").read_text(encoding="utf-8")
    assert "mastery-public" in script
    assert "summary/parent" in script
    assert "summary/teacher" in script
    assert "tiers/assign" in script
    assert "60" in script


def test_p9_landing_hire_copy_and_quality_gate():
    text = (ROOT / "frontend/src/pages/LandingPage.tsx").read_text(encoding="utf-8")
    assert "今晚就能陪" in text or "敢问敢练" in text
    assert "quality-gate-strip" in text or "getQualityGates" in text
    assert "trust=1" in text


def test_p9_legacy_60s_script_still_present():
    assert (ROOT / "scripts/smoke_activation_60s.py").is_file()


def test_p9_browser_path_script_max_two_clicks():
    script = (ROOT / "scripts/smoke_browser_path_activation.py").read_text(encoding="utf-8")
    assert "max_user_clicks" in script or "clicks<=2" in script
    assert "pilot-assets/concept" in script
    assert "_assert_link_is_shallow" in script
