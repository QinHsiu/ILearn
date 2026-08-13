"""Grade-band and gender theme selection for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

Band = Literal["primary", "junior", "senior"]
Gender = Literal["male", "female", "unspecified"]

_THEMES_DIR = Path(__file__).with_name("themes")
_VALID_GENDERS = frozenset({"male", "female", "unspecified"})


def band_for_grade(grade: int) -> Band:
    """Map K12 grade (1–12) to primary / junior / senior band."""
    if grade <= 6:
        return "primary"
    if grade <= 9:
        return "junior"
    return "senior"


def theme_key_for(grade: int, gender: str) -> str:
    """Build theme filename stem, e.g. ``primary_female``."""
    band = band_for_grade(grade)
    if gender not in _VALID_GENDERS:
        gender = "unspecified"
    return f"{band}_{gender}"


def load_theme_css(key: str) -> str:
    """Load CSS pack for the given theme key."""
    path = _THEMES_DIR / f"{key}.css"
    return path.read_text(encoding="utf-8")
