from pathlib import Path

from ilearn.providers.model_routing_config import load_model_routing_config


def test_load_from_explicit_json(tmp_path: Path):
    path = tmp_path / "model_routing.json"
    path.write_text(
        '{"routing":{"defaults":{"max_latency_ms":1000,"max_cost_per_call":0.01},'
        '"overrides":{"tutoring":"gpt-4.1"},'
        '"fallback":{"enabled":true,"default":"gpt-4o-mini"}}}',
        encoding="utf-8",
    )
    cfg = load_model_routing_config(path)
    assert cfg.defaults.max_latency_ms == 1000
    assert cfg.overrides["tutoring"] == "gpt-4.1"
    assert cfg.fallback.default == "gpt-4o-mini"


def test_missing_file_returns_builtin_defaults(tmp_path: Path, monkeypatch):
    missing = tmp_path / "nope.json"
    monkeypatch.delenv("ILEARN_MODEL_ROUTING_CONFIG", raising=False)
    cfg = load_model_routing_config(missing)
    assert cfg.fallback.enabled is True
    assert cfg.fallback.default == "gpt-4o-mini"
    assert cfg.overrides.get("grading_objective") == "gpt-4o-mini"
