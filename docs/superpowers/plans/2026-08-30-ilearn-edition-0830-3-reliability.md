# Edition 0830_3 Reliability (Tranche B) Implementation Plan

> **For agentic workers:** Use executing-plans. Checkbox steps for tracking.

**Goal:** Sync reliability hardening for sessions, LLM fallback, edge diagnosis/planning, graph cycles.

**Architecture:** Locks in storage + orchestrator; extend existing LLM/agents; add `graph_validator.py`.

**Tech Stack:** threading, existing RetryHandler, pydantic schemas unchanged.

## Global Constraints

- Keep sync Agent `run()` and `DiagnosisReport` / `LearningPlanReport` contracts.
- No deep-merge of session JSON.
- No new deps (tenacity/aiohttp).
- Paper size 20 unchanged.

### Tasks

1. SessionStore lock + cache + tests  
2. session_lock + Orchestrator wiring  
3. LLM retry/fallback + tests  
4. Diagnosis/Planning edge enrichment + tests  
5. GraphValidator + cognitive/KG hook + tests  
6. VERSION + full pytest  
