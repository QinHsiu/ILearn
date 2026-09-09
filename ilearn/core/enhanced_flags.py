"""Feature flags for edition_0909_1 enhanced merge (default off)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_KNOWN = (
    "ENABLE_ENHANCED_PROFILE",
    "ENABLE_ENHANCED_AGENTS",
    "ENABLE_ENHANCED_API",
)

_TRUE = frozenset({"1", "true", "yes", "on"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_bool(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in _TRUE


def _parse_features_yaml(text: str) -> dict[str, bool]:
    """Minimal ``key: bool`` parser — avoids a PyYAML hard dependency."""
    data: dict[str, bool] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key in _KNOWN:
            data[key] = _parse_bool(value)
    return data


@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, bool]:
    path = _repo_root() / "data" / "features.yaml"
    defaults = {k: False for k in _KNOWN}
    if not path.is_file():
        return defaults
    parsed = _parse_features_yaml(path.read_text(encoding="utf-8"))
    defaults.update(parsed)
    return defaults


def is_enhanced_enabled(name: str) -> bool:
    """Return whether an enhanced flag is on (env overrides YAML)."""
    if name not in _KNOWN:
        return False
    env = os.getenv(f"ILEARN_{name}")
    if env is not None and env.strip() != "":
        return _parse_bool(env)
    return bool(_load_yaml().get(name, False))


def clear_enhanced_flag_cache() -> None:
    """Clear YAML cache (tests / after editing features.yaml)."""
    _load_yaml.cache_clear()
