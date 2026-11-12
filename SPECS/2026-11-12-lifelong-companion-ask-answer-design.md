# ILearn Lifelong Companion — Ask + Answer Design

**Date:** 2026-11-12  
**Status:** P1 shipped + `/exp_loop` target met (2026-11-12)  
**Product arc:** Lifelong personal learning OS; Phase-1 education stages (primary → graduate); capability unlock **P1 Ask + Answer**; Evaluate becomes a tool.

---

## 1. Problem

ILearn today is strong on **Evaluate → Remediate** (assessment → grade → diagnose → plan → practice loop). A true personal learning agent must also **Ask, Answer, Plan, Predict, Evaluate**. Evaluate is only one capability.

Vision: one continuous identity across a human lifetime; Phase 1 focuses on **education career** (小学→研究生), not yet workplace/elder stages.

## 2. Goals / Non-goals

### Goals (P1)

1. Companion chat as primary entry (`POST /companion/chat`).
2. Intent router: `ask | answer | evaluate | plan | predict` (plan/predict stub messages).
3. Ask: clarify goals, stage, constraints; Socratic follow-ups; log to `event_log`.
4. Answer: curriculum retrieve + staged explanation; TutorRail / leak policy by `LifeStage` + `mode`.
5. Evaluate: call existing `MultiAgentOrchestrator` tools without replacing the pipeline.
6. Offline-capable demos (rule intent + retrieval summary when LLM unavailable).
7. Introduce `LifeStage` on profile (fields + routing hooks); content packs beyond primary math may still be thin.

### Non-goals (P1)

- Full Plan calendar / Predict models
- Full graduate thesis / oral pipelines
- Separate Life-OS repository (interface hooks only)
- Replacing host state machine with LangGraph/AutoGen

## 3. Decisions locked

| Decision | Choice |
| --- | --- |
| Lifetime scope | Yes — architecture must not hard-code “elementary only” |
| Phase-1 life window | Education stages primary → graduate (option B) |
| Architecture style | Deepen ILearn + `StagePlugin` hooks (route 1); defer split Life-OS repo |
| First capability | **P1 Ask + Answer** |
| Next content pack default | **B1 初中数学** (unless overridden) |
| Orchestration | Keep `HostStateMachineBackend` + `event_log` |

## 4. Capability model

```text
Companion Shell (chat entry)
        │ intent router
   ┌────┼────┬────┬────┐
  Ask Answer Plan Predict Evaluate
   │     │     │     │      │
   └─────┴──── evidence/memory (event_log, KnowledgeEvidence, citations)
```

| Capability | P1 behavior |
| --- | --- |
| Ask | Clarifying questions; Socratic turns; no final-answer leak in exam mode |
| Answer | Explain with citations or explicit miss; optional “要不要测一下” |
| Plan | Stub: “规划能力下一期开放” |
| Predict | Stub: “预测能力下一期开放” |
| Evaluate | Tool bridge into existing assess/grade/diagnose/plan pipeline |

## 5. Components

### 5.1 `LifeStage`

```text
early_childhood | primary | junior_high | senior_high | undergrad | graduate | career | midlife | elder
```

P1 actively supports: `primary` (full), `junior_high` (pack stretch), others (routing + honest “内容包未就绪”).

### 5.2 `CompanionAgent`

- Input: `session_id`, `message`, optional `mode` (`exam_tutor` | `open_learn`)
- **Multimodal I/O (P1 hooks, must not paint into a corner):**
  - Input modalities: `text` | `speech` | `image` (speech/image via `PerceptionAdapter` → `PerceptionOutput.text`)
  - API accepts either `message` **or** `perception` (`source_type`, `text`/`audio_ref`/`image_ref`, `confidence`)
  - Output always includes `reply` (text) **and** `speech` envelope for TTS consumers: `{ ssml_or_text, locale, speakable: bool }` — P1 may leave audio bytes to a future TTS adapter; do **not** omit the field
  - Do not require TTS runtime in P1; interface + passthrough text is enough
- Output: `{ intent, reply, speech, citations[], actions[], input_modality }`
- Actions may include `{ type: "start_assessment" }` / `{ type: "open_tutor", item_id }`

### 5.3 Rails

Reuse `TutorRail` / `AnswerLeakRail` / `HintLadderRail`.

| mode | leak policy |
| --- | --- |
| `exam_tutor` | Strict — no answer keys |
| `open_learn` | Softer — may show worked examples with citation |

### 5.4 API / UI

- `POST /sessions/{session_id}/companion/chat`
  - Body: `{ message?: str, mode?, perception?: { source_type, text?, audio_ref?, image_ref?, confidence? } }`
  - At least one of `message` or `perception.text` / resolved transcript required
- `POST /sessions/{session_id}/companion/transcribe` (thin wrapper over `SpeechAssessmentAdapter`) — returns `PerceptionOutput`; clients may then call `/companion/chat` with `perception`
- `GET /sessions/{session_id}/companion/history` (from `event_log` kinds `companion_*`)
- Frontend: Companion chat as default student entry candidate; keep assessment wizard reachable; UI may hide mic until TTS/ASR wired, but client types should already model `speech` + `perception`

### 5.5 Events

Append `OrchestrationEvent` with `kind` in:

- `companion_ask`
- `companion_answer`
- `companion_route_evaluate`
- `companion_stub_plan` / `companion_stub_predict`

## 6. Success metrics (for `/exp_loop`)

1. ≥60% of companion turns labeled ask/answer in non-assessment sessions  
2. Answer turns include citation **or** explicit no-hit  
3. Exam-mode leak regression suite remains green  
4. Offline companion path returns non-empty reply without API key  

## 7. Implementation phases

1. Schemas: `LifeStage`, companion message models  
2. Intent router (rules first; LLM optional)  
3. Ask/Answer handlers + rails  
4. Evaluate tool bridge  
5. API + minimal frontend chat  
6. Tests + AUDIT.md / README touch  
7. Optional: kick `/exp_loop` notebook under `content/exp/ilearn-companion-p1/`

## 8. Risks

| Risk | Mitigation |
| --- | --- |
| Chat becomes unconstrained homework-answer bot | Default `exam_tutor` for school-age; rails mandatory |
| LifeStage without content packs | Honest degradation messages |
| Scope creep into Plan/Predict | Stubs only in P1 |

## 9. Open follow-ups (post-P1)

- [x] Plan: executable week schedule (`companion_week_plan`)  
- [x] Predict: probe-gap / derailment risk (`companion_predict`)  
- [x] B1 junior-high math source pack  
- [x] Thin packs senior_high / undergrad / graduate (B2–B4)  
- [x] Career/midlife/elder stage packs + age-based LifeStage inference (thin hooks)  

---

## Spec self-review

- [x] No TBD placeholders for P1 scope  
- [x] Consistent with prior audit readiness (event_log, rails, host backend)  
- [x] Non-goals explicit  
- [x] `doc/` and `docs/` are gitignored in ILearn — canonical copy also at repo-root `SPECS/` for commit  
