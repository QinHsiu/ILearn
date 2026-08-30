"""Tests for process cache."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.cache import CacheManager, get_cache, load_json_cached


def test_cache_manager_ttl_expiry(monkeypatch):
    cache = CacheManager()
    cache.set("k", {"v": 1}, max_age=10)
    assert cache.get("k") == {"v": 1}
    monkeypatch.setattr("ilearn.core.cache.time.time", lambda: 1_000_000.0)
    cache.set("old", 1, max_age=1)
    monkeypatch.setattr("ilearn.core.cache.time.time", lambda: 1_000_002.0)
    assert cache.get("old") is None


def test_load_json_cached_hits_memory(tmp_path: Path):
    get_cache().clear()
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    first = load_json_cached(path)
    path.write_text(json.dumps({"a": 2}), encoding="utf-8")
    # same mtime sometimes on fast FS — touch mtime
    import os
    import time

    os.utime(path, (time.time() + 5, time.time() + 5))
    second = load_json_cached(path)
    assert first == {"a": 1}
    assert second == {"a": 2}
