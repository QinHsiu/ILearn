from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.migration import EvidenceMigrator
from ilearn.core.schemas import SessionState, StudentProfile
from ilearn.storage.sessions import SessionStore


def test_migrate_fills_missing_confidence_and_id():
    raw = {
        "session_id": "s1",
        "item_id": "i1",
        "knowledge_id": "frac_add_same",
        "correct": True,
        # no confidence, no evidence_id, no lane
    }
    out = EvidenceMigrator.migrate_evidence_entry(raw)
    assert out is not None
    assert out["confidence"] == 0.5
    assert out["evidence_id"]
    assert out["lane"] == "practice"


def test_migrate_maps_legacy_source_type_and_hint_count():
    raw = {
        "session_id": "s1",
        "item_id": "i1",
        "knowledge_id": "k1",
        "correct": False,
        "source_type": "probe",
        "hint_count": 2,
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    out = EvidenceMigrator.migrate_evidence_entry(raw)
    assert out is not None
    assert out["lane"] == "probe"
    assert out["hint_level"] == "low"
    assert "created_at" in out


def test_session_store_load_migrates_legacy_evidence(tmp_path: Path):
    store = SessionStore(tmp_path)
    profile = StudentProfile(region="北京", grade=5, age=11)
    state = store.create(profile)
    path = tmp_path / f"{state.session_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence_log"] = [
        {
            "session_id": state.session_id,
            "item_id": "item_a",
            "knowledge_id": "frac_add_same",
            "correct": True,
            # legacy: no confidence / evidence_id / lane
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    # bust cache if any
    store._cache.clear()
    store._cache_expires.clear()

    loaded = store.load(state.session_id)
    assert len(loaded.evidence_log) == 1
    ev = loaded.evidence_log[0]
    assert ev.confidence == 0.5
    assert ev.evidence_id
    assert ev.lane == "practice"
    # round-trip validate
    SessionState.model_validate(loaded.model_dump())
