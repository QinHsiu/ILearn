"""Simple in-process TTL cache for expensive JSON loads."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class CacheManager:
    """Memory-only cache with per-key TTL."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._expires_at: dict[str, float] = {}

    def get(self, key: str, max_age: int = 3600) -> Any | None:
        expires = self._expires_at.get(key)
        if expires is None or key not in self._values:
            return None
        if time.time() > expires:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
            return None
        # Refresh window relative to set time encoded as expires = set + max_age
        # Re-check using remaining life already stored at set().
        del max_age  # expiry absolute already stored
        return self._values[key]

    def set(self, key: str, value: Any, max_age: int = 3600) -> None:
        self._values[key] = value
        self._expires_at[key] = time.time() + max_age

    def clear(self) -> None:
        self._values.clear()
        self._expires_at.clear()


_GLOBAL_CACHE = CacheManager()


def get_cache() -> CacheManager:
    return _GLOBAL_CACHE


def load_json_cached(path: str | Path, *, max_age: int = 3600) -> Any:
    """Load JSON from disk with mtime-aware process cache."""
    resolved = Path(path).resolve()
    mtime = resolved.stat().st_mtime if resolved.exists() else 0.0
    key = f"json:{resolved}:{mtime}"
    cached = _GLOBAL_CACHE.get(key, max_age=max_age)
    if cached is not None:
        return cached
    with resolved.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _GLOBAL_CACHE.set(key, data, max_age=max_age)
    return data
