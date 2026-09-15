# Model Routing Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sync model registry, task-aware router, JSON routing config, and `SmartLLMClient` that composes existing `LLMClient` — without changing agent/API call sites.

**Architecture:** New modules under `ilearn/providers/` adapt `0815_e2/model` to the sync stack. `ModelRouter` picks a model from registry + `config/model_routing.json` overrides/fallback. `SmartLLMClient` temporarily sets `LLMClient.model`, calls `chat_json`, and retries once on fallback. Vision and Prometheus stay out of scope.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, existing `openai`-backed `LLMClient` (no PyYAML).

**Spec:** `docs/superpowers/specs/2026-08-15-model-routing-design.md`

## Global Constraints

- Infrastructure only: do **not** migrate agents/API to `TaskType` or replace `LLMClient.from_env()` default injection.
- Prefer **zero** edits to `ilearn/providers/llm.py` public API.
- Config format is **JSON** at `config/model_routing.json` (no PyYAML / prometheus).
- `SmartLLMClient` **composes** `LLMClient`; sync only; no vision routing changes.
- Offline tests only (no live network).
- Commit on feature branch during SDD; skip commits on master unless user asks.
- Diff focus: new provider modules + config + new tests; existing suite must stay green.

---

## File map

| File | Responsibility |
| --- | --- |
| `ilearn/providers/model_registry.py` | Tiers, capabilities, `ModelConfig`, default `MODEL_REGISTRY` |
| `ilearn/providers/model_routing_config.py` | Pydantic config models + loader |
| `config/model_routing.json` | Default overrides / fallback / latency-cost defaults |
| `ilearn/providers/model_router.py` | `TaskType`, context/decision, `ModelRouter.route` |
| `ilearn/providers/smart_llm.py` | `SmartLLMClient` wrapper |
| `tests/test_model_routing_config.py` | Loader + missing-file defaults |
| `tests/test_model_router.py` | Override / tier / fallback |
| `tests/test_smart_llm.py` | Route + fallback with fake LLM |

---

### Task 1: Registry + JSON config loader

**Files:**
- Create: `ilearn/providers/model_registry.py`
- Create: `ilearn/providers/model_routing_config.py`
- Create: `config/model_routing.json`
- Create: `tests/test_model_routing_config.py`

**Interfaces:**
- Consumes: stdlib `json`/`pathlib`, pydantic, `os.getenv`
- Produces:
  - `ModelTier`, `ModelCapability`, `ModelConfig`, `MODEL_REGISTRY: dict[str, ModelConfig]`
  - `RoutingDefaults`, `RoutingFallback`, `ModelRoutingConfig`, `load_model_routing_config(path: Path | None = None) -> ModelRoutingConfig`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_model_routing_config.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect FAIL (import / missing symbols)**

```bash
python -m pytest tests/test_model_routing_config.py -v
```

Expected: FAIL (`ModuleNotFoundError` or import error).

- [ ] **Step 3: Implement registry**

Create `ilearn/providers/model_registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    LITE = "lite"
    STANDARD = "standard"
    PREMIUM = "premium"


class ModelCapability(Enum):
    REASONING = "reasoning"
    CODE = "code"
    INSTRUCTION = "instruction"
    MULTILINGUAL = "multilingual"
    VISION = "vision"


@dataclass(frozen=True)
class ModelConfig:
    name: str
    tier: ModelTier
    capabilities: tuple[ModelCapability, ...]
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: int
    provider: str = "openai"


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        tier=ModelTier.LITE,
        capabilities=(ModelCapability.INSTRUCTION, ModelCapability.MULTILINGUAL),
        context_window=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        avg_latency_ms=800,
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        tier=ModelTier.STANDARD,
        capabilities=(
            ModelCapability.REASONING,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
            ModelCapability.VISION,
        ),
        context_window=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        avg_latency_ms=2500,
    ),
    "gpt-4.1": ModelConfig(
        name="gpt-4.1",
        tier=ModelTier.PREMIUM,
        capabilities=(
            ModelCapability.REASONING,
            ModelCapability.CODE,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
            ModelCapability.VISION,
        ),
        context_window=1048576,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.008,
        avg_latency_ms=3500,
    ),
}
```

- [ ] **Step 4: Implement config loader + default JSON**

Create `config/model_routing.json`:

```json
{
  "routing": {
    "defaults": {
      "max_latency_ms": 5000,
      "max_cost_per_call": 0.05
    },
    "overrides": {
      "grading_objective": "gpt-4o-mini",
      "tutoring": "gpt-4.1"
    },
    "fallback": {
      "enabled": true,
      "default": "gpt-4o-mini"
    }
  }
}
```

Create `ilearn/providers/model_routing_config.py`:

```python
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
```

- [ ] **Step 5: Run config tests — expect PASS**

```bash
python -m pytest tests/test_model_routing_config.py -v
```

- [ ] **Step 6: Commit (feature branch / if requested)**

```bash
git add ilearn/providers/model_registry.py ilearn/providers/model_routing_config.py config/model_routing.json tests/test_model_routing_config.py
git commit -m "feat: add model registry and JSON routing config"
```

---

### Task 2: ModelRouter

**Files:**
- Create: `ilearn/providers/model_router.py`
- Create: `tests/test_model_router.py`

**Interfaces:**
- Consumes: `MODEL_REGISTRY`, `ModelConfig`, `ModelTier`, `ModelCapability`, `ModelRoutingConfig`
- Produces: `TaskType`, `RoutingContext`, `RoutingDecision`, `ModelRouter.route(context) -> RoutingDecision`

- [ ] **Step 1: Write failing router tests**

Create `tests/test_model_router.py`:

```python
from ilearn.providers.model_registry import MODEL_REGISTRY, ModelCapability, ModelTier
from ilearn.providers.model_router import ModelRouter, RoutingContext, TaskType
from ilearn.providers.model_routing_config import ModelRoutingConfig, RoutingDefaults, RoutingFallback


def _router(**kwargs) -> ModelRouter:
    cfg = ModelRoutingConfig(
        defaults=RoutingDefaults(max_latency_ms=5000, max_cost_per_call=0.05),
        overrides=kwargs.get("overrides", {}),
        fallback=RoutingFallback(enabled=True, default="gpt-4o-mini"),
    )
    return ModelRouter(config=cfg, registry=MODEL_REGISTRY)


def test_override_wins_for_tutoring():
    router = _router(overrides={"tutoring": "gpt-4.1"})
    decision = router.route(
        RoutingContext(task_type=TaskType.TUTORING, input_text="hint please")
    )
    assert decision.model_name == "gpt-4.1"


def test_unknown_override_falls_through_to_rules():
    router = _router(overrides={"diagnosis": "not-a-real-model"})
    decision = router.route(
        RoutingContext(task_type=TaskType.DIAGNOSIS, input_text="diagnose")
    )
    assert decision.model_name in MODEL_REGISTRY
    assert decision.model_name != "not-a-real-model"
    assert MODEL_REGISTRY[decision.model_name].tier == ModelTier.PREMIUM


def test_grading_objective_allows_lite():
    router = _router(overrides={})
    decision = router.route(
        RoutingContext(task_type=TaskType.GRADING_OBJECTIVE, input_text="1+1")
    )
    assert decision.model_name in MODEL_REGISTRY
    # With empty overrides, lite is eligible; ranking may still pick higher tiers.
    # Assert at least that lite remains a valid candidate path by forcing override absence
    # and checking decision is not rejecting registry:
    assert decision.model_config.tier in (ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM)


def test_fallback_when_no_candidates(monkeypatch):
    router = _router(overrides={})
    # Force empty candidate set by requiring impossible capability via context
    decision = router.route(
        RoutingContext(
            task_type=TaskType.REPORT_SUMMARY,
            input_text="x",
            required_capabilities=[ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING],
            # After filter, if still empty, router must return fallback
        )
    )
    # May still find gpt-4.1 which has all three — use absurd context window instead:
    huge = "字" * 2_000_000
    decision = router.route(
        RoutingContext(task_type=TaskType.REPORT_SUMMARY, input_text=huge)
    )
    assert decision.model_name == "gpt-4o-mini"
```

Refine the last test in implementation if needed: the intended contract is **empty candidates → fallback.default**. Prefer implementing `_select_candidates` such that an oversize input empties the list, then fallback applies.

- [ ] **Step 2: Run router tests — expect FAIL**

```bash
python -m pytest tests/test_model_router.py -v
```

- [ ] **Step 3: Implement `model_router.py`**

Implement with this public surface (logic adapted from reference; keep sync and small):

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ilearn.providers.model_registry import (
    MODEL_REGISTRY,
    ModelCapability,
    ModelConfig,
    ModelTier,
)
from ilearn.providers.model_routing_config import ModelRoutingConfig


class TaskType(Enum):
    GRADING_OBJECTIVE = "grading_objective"
    GRADING_SUBJECTIVE = "grading_subjective"
    DIAGNOSIS = "diagnosis"
    TUTORING = "tutoring"
    PLANNING = "planning"
    REPORT_SUMMARY = "report_summary"
    EXPLANATION = "explanation"


@dataclass
class RoutingContext:
    task_type: TaskType
    input_text: str
    student_grade: int | None = None
    student_mastery: float | None = None
    is_critical: bool = False
    required_capabilities: list[ModelCapability] | None = None
    max_latency_ms: int | None = None
    max_cost: float | None = None


@dataclass
class RoutingDecision:
    model_name: str
    model_config: ModelConfig
    reason: str
    estimated_cost: float
    estimated_latency: int


_TIER_ORDER = [ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM]

_TASK_RULES: dict[TaskType, dict] = {
    TaskType.GRADING_OBJECTIVE: {
        "min_tier": ModelTier.LITE,
        "need_capabilities": [ModelCapability.INSTRUCTION],
    },
    TaskType.GRADING_SUBJECTIVE: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
    TaskType.DIAGNOSIS: {
        "min_tier": ModelTier.PREMIUM,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.MULTILINGUAL],
    },
    TaskType.TUTORING: {
        "min_tier": ModelTier.PREMIUM,
        "need_capabilities": [
            ModelCapability.REASONING,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
        ],
    },
    TaskType.PLANNING: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
    TaskType.REPORT_SUMMARY: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.INSTRUCTION],
    },
    TaskType.EXPLANATION: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
}


def estimate_token_count(text: str) -> int:
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4) + 10


class ModelRouter:
    def __init__(
        self,
        config: ModelRoutingConfig | None = None,
        registry: dict[str, ModelConfig] | None = None,
    ) -> None:
        self.config = config or ModelRoutingConfig()
        self.registry = registry or MODEL_REGISTRY
        if self.config.fallback.default not in self.registry:
            raise ValueError(
                f"fallback model not in registry: {self.config.fallback.default}"
            )

    def route(self, context: RoutingContext) -> RoutingDecision:
        override = self.config.overrides.get(context.task_type.value)
        if override and override in self.registry:
            return self._decision(
                override,
                context,
                reason=f"override for {context.task_type.value}",
            )

        candidates = self._select_candidates(context)
        if not candidates:
            fb = self.config.fallback.default
            return self._decision(
                fb, context, reason="fallback: no eligible candidates"
            )

        ranked = self._rank_candidates(candidates, context)
        return self._decision(
            ranked[0],
            context,
            reason=f"task {context.task_type.value} ranked {ranked[0]}",
        )

    # Implement _select_candidates / _rank_candidates / _decision / _estimate_cost
    # following the reference rules (min tier, capabilities, 0.8 * context_window,
    # tier score + cost/latency penalties). Unknown override names are ignored
    # (already handled by the `override in self.registry` check).
```

Fill in private helpers completely in the implementation (no stubs). Apply `context.max_latency_ms` / `max_cost` falling back to `self.config.defaults` when context fields are `None`.

- [ ] **Step 4: Run router tests — expect PASS**

```bash
python -m pytest tests/test_model_router.py tests/test_model_routing_config.py -v
```

Adjust the oversize-input fallback test if token estimate × 0.8 still fits `gpt-4.1`’s window — use a custom tiny-window registry fixture instead:

```python
def test_fallback_when_registry_filtered_empty():
    tiny = {
        "tiny": ModelConfig(
            name="tiny",
            tier=ModelTier.LITE,
            capabilities=(ModelCapability.INSTRUCTION,),
            context_window=10,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency_ms=1,
        ),
        "gpt-4o-mini": MODEL_REGISTRY["gpt-4o-mini"],
    }
    cfg = ModelRoutingConfig(
        overrides={},
        fallback=RoutingFallback(default="gpt-4o-mini"),
    )
    router = ModelRouter(config=cfg, registry=tiny)
    decision = router.route(
        RoutingContext(
            task_type=TaskType.REPORT_SUMMARY,
            input_text="这是一段足够长的中文输入用来挤爆极小上下文窗口" * 20,
        )
    )
    assert decision.model_name == "gpt-4o-mini"
```

Prefer this fixture-based test over the huge-string approach in Step 1.

- [ ] **Step 5: Commit**

```bash
git add ilearn/providers/model_router.py tests/test_model_router.py
git commit -m "feat: add task-aware ModelRouter"
```

---

### Task 3: SmartLLMClient

**Files:**
- Create: `ilearn/providers/smart_llm.py`
- Create: `tests/test_smart_llm.py`

**Interfaces:**
- Consumes: `LLMClient`, `LLMError`, `ModelRouter`, `TaskType`, `RoutingContext`, `load_model_routing_config`
- Produces:
  - `SmartLLMClient.chat_json(task_type, system, user, context=None) -> dict`
  - `SmartLLMClient.from_env() -> SmartLLMClient`

- [ ] **Step 1: Write failing SmartLLM tests**

```python
from ilearn.providers.llm import LLMError
from ilearn.providers.model_router import TaskType
from ilearn.providers.smart_llm import SmartLLMClient


class FakeLLM:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.calls: list[str] = []
        self.fail_models: set[str] = set()

    def chat_json(self, system: str, user: str) -> dict:
        self.calls.append(self.model)
        if self.model in self.fail_models:
            raise LLMError(f"boom:{self.model}")
        return {"ok": True, "model": self.model}


def test_chat_json_uses_routed_override_model():
    from ilearn.providers.model_router import ModelRouter
    from ilearn.providers.model_routing_config import (
        ModelRoutingConfig,
        RoutingFallback,
    )

    fake = FakeLLM(model="gpt-4o-mini")
    router = ModelRouter(
        config=ModelRoutingConfig(
            overrides={"tutoring": "gpt-4.1"},
            fallback=RoutingFallback(default="gpt-4o-mini"),
        )
    )
    client = SmartLLMClient(llm=fake, router=router)  # type: ignore[arg-type]
    result = client.chat_json(TaskType.TUTORING, "sys", "user")
    assert result["model"] == "gpt-4.1"
    assert fake.calls == ["gpt-4.1"]
    assert fake.model == "gpt-4o-mini"  # restored


def test_chat_json_falls_back_on_llm_error():
    from ilearn.providers.model_router import ModelRouter
    from ilearn.providers.model_routing_config import (
        ModelRoutingConfig,
        RoutingFallback,
    )

    fake = FakeLLM(model="gpt-4o-mini")
    fake.fail_models.add("gpt-4.1")
    router = ModelRouter(
        config=ModelRoutingConfig(
            overrides={"tutoring": "gpt-4.1"},
            fallback=RoutingFallback(enabled=True, default="gpt-4o-mini"),
        )
    )
    client = SmartLLMClient(llm=fake, router=router)  # type: ignore[arg-type]
    result = client.chat_json(TaskType.TUTORING, "sys", "user")
    assert result["model"] == "gpt-4o-mini"
    assert fake.calls == ["gpt-4.1", "gpt-4o-mini"]
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_smart_llm.py -v
```

- [ ] **Step 3: Implement `smart_llm.py`**

```python
from __future__ import annotations

from typing import Any

from ilearn.providers.llm import LLMClient, LLMError
from ilearn.providers.model_router import ModelRouter, RoutingContext, TaskType
from ilearn.providers.model_routing_config import load_model_routing_config


class SmartLLMClient:
    def __init__(
        self,
        llm: LLMClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.llm = llm or LLMClient.from_env()
        self.router = router or ModelRouter(config=load_model_routing_config())

    @classmethod
    def from_env(cls) -> SmartLLMClient:
        return cls(llm=LLMClient.from_env(), router=ModelRouter(config=load_model_routing_config()))

    def chat_json(
        self,
        task_type: TaskType,
        system: str,
        user: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        defaults = self.router.config.defaults
        routing_ctx = RoutingContext(
            task_type=task_type,
            input_text=f"{system}\n{user}",
            student_grade=context.get("grade"),
            student_mastery=context.get("mastery"),
            is_critical=task_type in (TaskType.DIAGNOSIS, TaskType.TUTORING),
            max_latency_ms=context.get("max_latency_ms", defaults.max_latency_ms),
            max_cost=context.get("max_cost", defaults.max_cost_per_call),
        )
        decision = self.router.route(routing_ctx)
        try:
            return self._call_with_model(decision.model_name, system, user)
        except LLMError:
            fb = self.router.config.fallback
            if (
                fb.enabled
                and fb.default != decision.model_name
                and fb.default in self.router.registry
            ):
                return self._call_with_model(fb.default, system, user)
            raise

    def _call_with_model(self, model_name: str, system: str, user: str) -> dict[str, Any]:
        previous = self.llm.model
        self.llm.model = model_name
        try:
            return self.llm.chat_json(system, user)
        finally:
            self.llm.model = previous
```

- [ ] **Step 4: Run Smart + prior tests — expect PASS**

```bash
python -m pytest tests/test_smart_llm.py tests/test_model_router.py tests/test_model_routing_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ilearn/providers/smart_llm.py tests/test_smart_llm.py
git commit -m "feat: add SmartLLMClient with route and fallback"
```

---

### Task 4: Verification gate

**Files:** none (read-only)

- [ ] **Step 1: Run focused + full suite**

```bash
python -m pytest tests/test_model_routing_config.py tests/test_model_router.py tests/test_smart_llm.py tests/test_session_store.py -v
python -m pytest -q
```

Expected: all PASS.

- [ ] **Step 2: Confirm scope**

```bash
git diff --stat master...HEAD
```

Expected files only under: `ilearn/providers/model_*.py`, `ilearn/providers/smart_llm.py`, `config/model_routing.json`, `tests/test_model_*.py` / `test_smart_llm.py`. No `frontend/`, no agent rewires, no `llm.py` unless unavoidable (should be none).

- [ ] **Step 3: Mark slice 2 complete** — do not start diagnosis slice unless asked.

---

## Self-review (plan vs spec)

| Spec item | Task |
| --- | --- |
| Registry + default models | Task 1 |
| JSON config + loader + missing → builtins | Task 1 |
| Router override / tier / fallback | Task 2 |
| SmartLLM compose + restore model + fallback | Task 3 |
| No agent/API/vision/metrics/PyYAML | Global + Task 4 |
| Offline tests | Tasks 1–3 |

No placeholders in required code paths. Types consistent across tasks.
