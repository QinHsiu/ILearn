# Companion Ask + Answer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement in-session with TDD.

**Goal:** Add Companion chat entry with Ask/Answer intents; Evaluate becomes a callable tool; Plan/Predict stubbed.

**Architecture:** New `CompanionAgent` + rule intent router; reuse CurriculumRetriever, TutorRails, MultiAgentOrchestrator; persist companion turns on `event_log`.

**Tech Stack:** FastAPI, Pydantic v2, existing ILearn agents/storage.

## Global Constraints

- Host state machine remains default; no AutoGen/LangGraph dependency
- Offline path must work without LLM
- Exam mode leak rails mandatory
- `doc/`/`docs/` gitignored — commit plans under `SPECS/`

---

### Task 1: Schemas

- [ ] Add `LifeStage`, `CompanionIntent`, `CompanionMode`, `CompanionAction`, `CompanionReply`
- [ ] Add `CompanionSpeechOut`, `CompanionPerceptionIn` (voice/image hooks)
- [ ] Optional `StudentProfile.life_stage`
- [ ] Tests for defaults / inference helper + speech envelope always present

### Task 2: CompanionAgent

- [ ] Failing tests: route ask/answer/evaluate/plan/predict
- [ ] Implement `ilearn/agents/companion.py` (rules + optional LLM)
- [ ] Accept text **or** `PerceptionOutput` / perception dict as input
- [ ] Answer uses retriever; Ask returns clarifying question
- [ ] Every reply fills `speech.ssml_or_text` (= reply text in P1)
- [ ] Log events via `append_orchestration_event`

### Task 3: Orchestrator bridge + API

- [x] `MultiAgentOrchestrator.companion_chat(...)`
- [x] `POST /sessions/{id}/companion/chat` (message and/or perception)
- [x] `POST /sessions/{id}/companion/transcribe` → SpeechAssessmentAdapter hook
- [x] Evaluate action triggers assessment generation message/action

### Task 4: Frontend companion entry + voice UI

- [x] Wizard step「同伴对话」after onboard
- [x] `CompanionChat` + mic/TTS hooks + client API types
- [x] Evaluate → advance to assessment step

### Task 5: Docs + ship

- [x] README / INTRODUCTION / AUDIT touch
- [x] Pytest / Vitest green; commit + PR (#42)
