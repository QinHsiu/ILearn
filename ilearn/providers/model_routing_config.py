from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


class RoutingDefaults(BaseModel):
    max_latency_ms: int = 5000
    max_cost_per_call: float = 0.05


class RoutingFallback(BaseModel):
    enabled: bool = True
    default: str = "gpt-4o-mini"


class ModelRoutingConfig(BaseModel):
    defaults: RoutingDefaults = Field(default_factory=RoutingDefaults)
    overrides: dict[str, str] = Field(default_factory=dict)
    fallback: RoutingFallback = Field(default_factory=RoutingFallback)


def _builtin_defaults() -> ModelRoutingConfig:
    return ModelRoutingConfig(
        defaults=RoutingDefaults(),
        overrides={
            "grading_objective": "gpt-4o-mini",
            "tutoring": "gpt-4.1",
        },
        fallback=RoutingFallback(),
    )


def load_model_routing_config(path: Path | None = None) -> ModelRoutingConfig:
    if path is None:
        env = os.getenv("ILEARN_MODEL_ROUTING_CONFIG")
        path = Path(env) if env else Path.cwd() / "config" / "model_routing.json"
    if not path.is_file():
        return _builtin_defaults()
    raw = json.loads(path.read_text(encoding="utf-8"))
    routing = raw.get("routing", raw)
    return ModelRoutingConfig.model_validate(routing)
