# Slice 2: Model routing infrastructure

**Date:** 2026-08-15  
**Status:** Approved for planning  
**Parent program:** Adapt `doc/deepseek_edition/0815_e2` into main ILearn (weekly vertical slices)  
**Reference:** `doc/deepseek_edition/0815_e2/model/`  
**Prior slice:** Session metadata listing (`list_all_metadata`) — complete on master

## Context

ILearn today uses a single sync `ilearn.providers.llm.LLMClient` (`chat_json`, `grade_image_json`) configured via env (`ILEARN_LLM_*`, `ILEARN_VISION_MODEL`). Agents and the API inject this client directly. The `0815_e2` reference adds a multi-model registry, task-aware router, Smart client with fallback, and YAML routing config (async OpenAI + Prometheus). Slice 2 adapts the **infrastructure** into the existing sync stack without replacing call sites.

## Goals

- Ship `ModelRegistry`, `ModelRouter`, JSON routing config, and sync `SmartLLMClient` that **composes** `LLMClient`.
- Support task-type overrides, tier/capability filtering, and fallback model selection offline-testable.
- Leave agent/API injection on plain `LLMClient`; do not force Smart as default `from_env()`.
- Zero new runtime dependencies (JSON + Pydantic, no PyYAML / prometheus_client).

## Non-goals

- Prometheus `/metrics` or monitoring endpoints.
- Async OpenAI client / multi-provider API key plumbing.
- Migrating grading, diagnosis, tutor, planning, etc. to pass `TaskType`.
- Changing `grade_image_json` / vision routing (still env + existing `LLMClient`).
- Replacing `LLMClient.from_env()` return type.

## Approach

Thin sync stack under `ilearn/providers/` + `config/model_routing.json`, adapting reference behavior to production layout.

## Components

### 1. `ilearn/providers/model_registry.py`

- Enums: `ModelTier` (`lite` | `standard` | `premium`), `ModelCapability` (`reasoning`, `code`, `instruction`, `multilingual`, `vision`).
- `ModelConfig` dataclass (or Pydantic): `name`, `tier`, `capabilities`, `context_window`, `cost_per_1k_input`, `cost_per_1k_output`, `avg_latency_ms`, `provider` (default `"openai"`).
- Default `MODEL_REGISTRY` dict with at least: `gpt-4o-mini` (lite), `gpt-4o` (standard + vision), `gpt-4.1` (premium + vision). Costs/latency are catalog estimates for ranking only.

### 2. `ilearn/providers/model_router.py`

- `TaskType` enum: `grading_objective`, `grading_subjective`, `diagnosis`, `tutoring`, `planning`, `report_summary`, `explanation` (same values as reference).
- `RoutingContext`: `task_type`, `input_text`, optional `student_grade`, `student_mastery`, `is_critical`, `required_capabilities`, `max_latency_ms`, `max_cost`.
- `RoutingDecision`: `model_name`, `model_config`, `reason`, `estimated_cost`, `estimated_latency`.
- `ModelRouter(config, registry=MODEL_REGISTRY)`:
  1. If `overrides[task_type]` present and name in registry → that model.
  2. Else candidates by min-tier + required capabilities for the task; drop models whose context window cannot hold ~80% of estimated input tokens.
  3. Rank quality-first (tier), with light penalties for over-budget cost/latency when bounds provided.
  4. If no candidates → `fallback.default` (must exist in registry).

Token estimate: simple CJK heuristic (no tokenizer dependency).

### 3. `config/model_routing.json` + loader

Default file at repo `config/model_routing.json`:

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

- Loader: `ilearn/providers/model_routing_config.py` — Pydantic models; `load_model_routing_config(path: Path | None = None)`.
- Missing file → equivalent in-code defaults (same shape; no monitoring block).
- Path resolution: explicit path, else `Path.cwd() / "config/model_routing.json"`, else package-relative fallback if documented in loader (prefer cwd + optional `ILEARN_MODEL_ROUTING_CONFIG` env for tests).

### 4. `ilearn/providers/smart_llm.py`

- `SmartLLMClient(llm: LLMClient | None = None, router: ModelRouter | None = None)`.
- Factory: `SmartLLMClient.from_env()` builds `LLMClient.from_env()` + router from loaded config (for future use; API does not switch to it this slice).
- `chat_json(task_type: TaskType, system: str, user: str, context: dict | None = None) -> dict`:
  - Build `RoutingContext` from task + `system+"\n"+user` + optional grade/mastery from context; apply config defaults for max latency/cost when context omits them.
  - `decision = router.route(...)`.
  - Temporarily set inner `llm.model` to `decision.model_name`, call `llm.chat_json`, restore previous model in `finally`.
  - On `LLMError`: if fallback enabled and fallback name ≠ primary, retry once with fallback model; else re-raise.
- Does not implement vision routing; callers keep using `LLMClient.grade_image_json`.

### 5. Unchanged

- `ilearn/providers/llm.py` public API (prefer **zero** edits).
- `ilearn/api/app.py` and agent constructors continue to use `LLMClient.from_env()`.

## Data flow

```
TaskType + prompts (+ optional student context)
        │
        ▼
 ModelRouter.route  ← registry + model_routing.json
        │
        ▼
 RoutingDecision.model_name
        │
        ▼
 SmartLLMClient → LLMClient.chat_json(model=…)
        │
        └─ on failure → fallback.default (once)
```

## Error handling

- Unknown override model name: skip override, continue with tier rules (or fall through to fallback); document in reason string.
- Empty registry / missing fallback name: raise clear `ValueError` at router init or first `route`.
- Smart client: preserve `LLMError` semantics after exhausted fallback.

## Testing

- `tests/test_model_router.py`: override wins; tier filter excludes lite for diagnosis; empty candidates → fallback; token/context filtering smoke.
- `tests/test_smart_llm.py`: stub/fake `LLMClient` recording `model` used; assert routed model; assert fallback after primary raises `LLMError`.
- No live network calls.
- Full existing suite remains green.

## Success criteria

- New modules + config + tests land; agents/API behavior unchanged.
- Diff does not add PyYAML or prometheus.
- Spec/plan docs under `docs/superpowers/` (gitignored locally is fine).

## Follow-on

Later slices (diagnosis / scaffold / etc.) may inject `SmartLLMClient` and pass `TaskType`. Slice 3+ UI will not depend on this directly.
