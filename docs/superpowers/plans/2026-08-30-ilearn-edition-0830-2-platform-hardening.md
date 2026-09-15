# Edition 0830_2 Platform Hardening (Tranche A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship settings, logging, cache, rate limit, and submit validators without changing Agent diagnosis/plan schemas.

**Architecture:** Pure library modules under `ilearn/core/`; wire into FastAPI `create_app`, `LLMClient.from_env`, and graph loaders. Sync-only.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, pytest, existing python-dotenv.

## Global Constraints

- Full diagnostic paper stays **exactly 20** items.
- Do not break existing TestClient API flows.
- Empty answer strings remain allowed on submit.
- Rate limit default: 100 req / 60s; disable via `ILEARN_RATE_LIMIT_ENABLED=0` for stress/debug.
- No `pydantic-settings` dependency required.
- Do not commit `doc/`.

---

### Task 1: Settings

**Files:** Create `ilearn/core/settings.py`; Test `tests/test_settings_0830_2.py`; Modify `.env.example`

- [ ] Implement `ILearnSettings` + `get_settings()` / `clear_settings_cache()`
- [ ] Fields: llm_*, mastery_threshold, data paths, rate_limit_*, auth demo creds, retriever_backend, sessions_dir
- [ ] Wire `LLMClient.from_env` to settings

### Task 2: Logging + Retry

**Files:** Create `ilearn/core/logging_utils.py`; Test `tests/test_logging_utils_0830_2.py`

- [ ] `get_logger`, sync `log_execution`, sync `RetryHandler.with_retry`

### Task 3: Cache + graph loaders

**Files:** Create `ilearn/core/cache.py`; Modify `knowledge_graph.py`, `cognitive_profile.py`; Test `tests/test_cache_0830_2.py`

- [ ] Memory TTL cache; `load_json_file(path)` uses cache keyed by resolved path + mtime

### Task 4: Rate limiter

**Files:** Create `ilearn/core/rate_limiter.py`; Modify `ilearn/api/app.py`; Test `tests/test_rate_limit_0830_2.py`

- [ ] Middleware + header; 429 when exceeded

### Task 5: Validators + submit wire

**Files:** Create `ilearn/core/validators.py`; Modify `app.py` SubmitRequest / submit; Test `tests/test_validators_0830_2.py`

- [ ] Reject XSS / overlong / bad keys; allow empty values

### Task 6: VERSION + regression

- [ ] Update VERSION.md; run `pytest -q`
