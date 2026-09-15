# Edition 0830_2 Tranche A — Platform Hardening Design

**Date:** 2026-08-30  
**Status:** Approved (scope A)  
**Source:** `doc/edition_0830_2.txt` (subset)

## Goal

Add cross-cutting platform hardening without changing diagnosis/planning business contracts or the 20-item paper.

## In scope

1. `ILearnSettings` reading existing `ILEARN_*` env vars (no new required deps; pydantic BaseModel + dotenv).
2. Structured logging + sync `log_execution` + sync `RetryHandler`.
3. Process-memory TTL `CacheManager`; KG / cognitive graph JSON loads via cache.
4. Sliding-window rate limit middleware (configurable; remaining header).
5. Submit answer validation (length, key charset, XSS patterns) — empty answers still allowed for API compatibility.
6. Unit/middleware tests; wire settings into `LLMClient.from_env` and `create_app` auth env reads.

## Out of scope

SOLO/`DiagnosisResult` rewrite, async batch diagnose, progress BackgroundTasks API, react-router lazy load / virtualizer.

## Interfaces

- `get_settings() -> ILearnSettings` (lru_cache)
- `CacheManager.get/set`, `load_json_cached(path)`
- `RateLimiter.is_allowed(client_id) -> (bool, remaining)`
- `RateLimitMiddleware` registered in `create_app` when `rate_limit_enabled`
- `validate_submit_answers(answers: dict[str, str]) -> dict[str, str]` used by submit endpoint
