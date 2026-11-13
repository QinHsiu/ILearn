# P4 — L2 Wiki Knowledge Memory

**Date:** 2026-11-13  
**Status:** Implementing  
**Parent:** `SPECS/2026-11-13-learner-state-architecture.md`

## Goal

Human-readable, agent-queryable wiki pages with **BM25** retrieval, optionally boosted by L1 `LearnerState.mastery` `skill_id` links. Runs **in parallel** with Curriculum RAG — does not replace it.

## Acceptance

1. Ingest curriculum sources + concept markdown into wiki pages  
2. BM25 search returns ranked pages with `skill_ids`  
3. Weak skills in LearnerState boost matching wiki pages  
4. Companion Answer merges wiki hits into citations (source_label marks `wiki`)  
5. Simple skill-graph edges (shared `skill_id`) for related-page expand  
6. Offline / no extra pip deps (stdlib BM25)

## Non-goals

- Full GraphRAG / vector DB  
- SQLite FTS5 L3 session search (later)  
- Replacing CurriculumAgent backend
