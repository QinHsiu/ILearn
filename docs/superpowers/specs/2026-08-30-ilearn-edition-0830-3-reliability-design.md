# Edition 0830_3 Tranche B — Reliability Hardening Design

**Date:** 2026-08-30  
**Status:** Approved (scope B)  
**Source:** `doc/edition_0830_3.txt` (adapted)

## Goal

Improve concurrency safety, LLM degradation, diagnosis/planning edge cases, and graph cycle detection — sync stack only.

## In scope

1. `SessionStore`: process `threading.RLock` + optional TTL read cache (invalidate on save/delete). No deep-merge.
2. `SessionLockManager`: per-`session_id` `RLock`; Orchestrator mutators hold lock across load→mutate→save.
3. `LLMClient.chat_json(..., fallback=True)` + rule fallback JSON; wrap `_call_chat` with `RetryHandler`.
4. Diagnosis enrichment `data_status` / `message` for empty / sparse evidence; Planning scientific_plan handles no-weak / insufficient.
5. `GraphValidator` cycle detection; hook into cognitive + knowledge graph validation.

## Out of scope

Async SessionStore, new aiohttp LLM client, tenacity, async PDF queue.
