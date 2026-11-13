# Versioned Learner State + Layered Memory Architecture

**Date:** 2026-11-13  
**Status:** Implementing (user-supplied architecture)  
**Depends on:** Host state machine + `event_log` (AUDIT readiness)

## Goal

Upgrade session-scoped `StudentProfile` / append-only `event_log` into:

- **L1** Versioned `LearnerState` (projectable, hash-chained, single-writer)
- **P1** Time-aware proactive scheduler (SM-2 + dispatch receipts)
- **P2** Experience store as read-only prior (no RL rewrite of pipeline)
- **P3** State-machine template registry (K12 wraps existing host FSM)

## Acceptance

| Phase | Gate |
| --- | --- |
| P0 | Two sessions a week apart consume the same projected `LearnerState`; `state_hash` chain verifies |
| P1 | Due SM-2 window → `ProactiveDispatchReceipt` with `evidence_refs` + `state_version` |
| P2 | Decision context may include `experience_refs`; retrieve is read-only |
| P3 | K12 flow registered as first template; schema stays cross-template compatible |

## Follow-ups

- [x] L2 wiki BM25+skill graph (P4) — see `SPECS/2026-11-13-wiki-l2-memory-design.md`
- Online RL / ProactRL training — out of scope
- Replacing HostStateMachineBackend runtime — out of scope
- L3 SQLite FTS5 session memory — later
