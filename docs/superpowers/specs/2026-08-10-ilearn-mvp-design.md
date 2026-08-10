# ILearn MVP Design Spec

**Date:** 2026-08-10  
**Status:** Approved for implementation  
**Location:** `projects/ILearn`  
**Approach:** Pipeline modules + thin orchestrator (not LangGraph-first)

## 1. Goal

Build **ILearn**, a personalized learning agent MVP that closes the loop:

**practice → step-level grade & feedback → diagnosis → learning plan → (later) practice again**

MVP delivers three product capabilities in one vertical slice:

1. Personalized learning planning (post-assessment report)
2. Homework tutoring substrate (step-level grading + error tags; no multi-turn Socratic chat yet)
3. Learning-situation diagnosis (knowledge gaps + coarse ability scores)

## 2. Scope Decisions (Locked)

| Decision | Choice |
|----------|--------|
| First slice | End-to-end MVP loop |
| Subject / grades | Elementary math, grades 4–6 |
| Surfaces | Web + CLI/API (shared core) |
| Curriculum | Fixed pilot: Beijing + Renjiao-oriented local pack; `CurriculumProvider` swappable |
| LLM | OpenAI-compatible API via `.env` (`BASE_URL`, `API_KEY`, model name) |
| Acceptance | Demo loop + minimal public/self-built eval harness |
| Default assessment size | **20 items** |
| Difficulty mix | 50% easy / 40% medium / 10% hard → **10 / 8 / 2** |
| Item-type mix | 40% choice / 40% fill / 20% constructed → **8 / 8 / 4** |
| Answer modalities | Keyboard text only |
| Image / VL grading | **Out of MVP** |
| Live web curriculum crawl | **Out of MVP** |
| Multi-subject | **Out of MVP** |

## 3. Architecture

Python monorepo with core logic separated from UI:

```
ilearn/
  core/           # profile, assessment, grading, diagnosis, planning, orchestrator
  providers/      # CurriculumProvider, LLMClient
  storage/        # session artifacts as JSON files under data/sessions/ (no DB in MVP)
  api/            # FastAPI
  cli/            # end-to-end run + eval
  web/            # Streamlit wizard; talks to FastAPI over HTTP only
  eval/           # minimal grading eval runner + fixtures
  data/pilot/     # Beijing·Renjiao elementary math knowledge + item templates
```

### 3.1 Pipeline

1. Input `region`, `grade`, `age` → `StudentProfile`  
   - `grade` must be 4, 5, or 6.  
   - Any `region` string is stored; MVP **always** loads the Beijing·Renjiao pilot pack. If `region` is not Beijing-equivalent, the report includes an explicit mismatch disclaimer (no silent pretend-localization).
2. `AssessmentBuilder` builds a 20-item paper from pilot curriculum
3. Student submits text answers
4. `StepGrader` emits per-item step results and controlled error tags
5. `Diagnoser` aggregates knowledge mastery + coarse abilities
6. `Planner` emits a 1–2 week plan (JSON + Markdown)
7. Persist session; Web and CLI read the same report

`Orchestrator` only sequences steps and validates schemas. Business rules live in modules.

### 3.2 Provider seams

- `CurriculumProvider`: MVP implementation `PilotBeijingRenjiaoProvider`; later RAG/web sources plug in here
- `LLMClient`: OpenAI-compatible chat completions; used for constructed-response grading, narrative polish, optional template fill when templates are insufficient

## 4. Assessment & Pilot Bank

### 4.1 Curriculum pack (`data/pilot/`)

Each knowledge node includes:

- `id`, `grade`, `name`
- ability tags (`logic`, `spatial`, `mental_math`, …)
- item templates with slots (numbers / scenarios)

Cover core grade 4–6 topics (fractions, perimeter/area, simple equations, etc.). Prefer fewer accurate nodes over broad shallow coverage.

### 4.2 Assembly rules

1. Filter knowledge pool by grade
2. Sample to satisfy difficulty quotas (10 / 8 / 2)
3. Instantiate to satisfy type quotas (8 / 8 / 4)
4. Fail closed if quotas cannot be met (do not silently skew mixes)

### 4.3 Item schema

- `id`, `stem`, `type`, `difficulty`, `knowledge_ids`
- `answer_key` (required for choice; preferred for fill)
- `rubric_steps[]` (required for constructed; optional enrichment for others)

Generation: **template-first (primary path for MVP)**. STEM/math items are the focus (elementary math grades 4–6). LLM fill is fallback only when a template cannot instantiate, and must stay within curriculum tags. No free-form off-syllabus items.

## 5. Step-Level Grading

### 5.1 `GradeResult` (per item)

- `final_correct`: bool
- `steps[]`: parsed / aligned student steps
- `step_results[]`: per-step correct / incorrect / partial + short comment
- `error_tags[]`: from controlled vocab  
  `concept_gap` | `calc_error` | `misread` | `method_wrong` | `incomplete`
- `knowledge_ids[]`: implicated weak knowledge
- `hint_level_suggestion`: reserved for future tutoring (stored, not used for multi-turn in MVP)
- `grading_degraded`: optional flag when LLM/schema fails

### 5.2 Strategy

1. Choice / rule-gradable fill: deterministic check against `answer_key`; if wrong, LLM maps to steps/error tags against rubric
2. Constructed / hard fill: LLM aligns student text to `rubric_steps`, scores steps, assigns tags
3. LLM outputs must pass JSON schema; one retry; then degrade to final-correct-only with `grading_degraded=true`

Borrowed *interface ideas* (not code): TutorGym / BEA step feedback shape; Socratic “stuck-point” as diagnosis input only.

## 6. Diagnosis & Learning Plan

### 6.1 `DiagnosisReport`

- Per-knowledge mastery: score rate, error-tag distribution, level (`mastered` / `unstable` / `weak`)
- Coarse ability radar (0–100): derived from knowledge ability tags + error heuristics; labeled as **heuristic, not psychometric**
- Prioritized intervention list (**Top-5**) with short “why / what to fix first”
- Provenance: explicit pilot curriculum label (e.g. Beijing · Renjiao · grade N)

Numeric/tag fields must be traceable to item ids. LLM may polish prose only.

### 6.2 `LearningPlanReport`

Inputs: diagnosis + optional daily minutes (default 30–45).

Outputs (JSON + Markdown):

- 1–2 week goal and milestones
- Day-level tasks: review focus, practice volume suggestion, self-check method (same subject)
- Links from tasks → weak knowledge ids → curriculum entries
- Disclaimer: assistant suggestion; does not replace teacher evaluation

Dynamic re-plan after further practice is an interface stub only; MVP emits **one plan after the initial assessment**.

Web shows mastery table, ability radar, plan timeline; export Markdown required; PDF optional later.

## 7. API, Web, CLI

### 7.1 FastAPI

- `POST /sessions` — create profile (region/grade/age)
- `POST /sessions/{id}/assessment` — build 20-item paper
- `POST /sessions/{id}/submit` — text answers
- `POST /sessions/{id}/grade`
- `POST /sessions/{id}/diagnose`
- `POST /sessions/{id}/plan`
- `GET /sessions/{id}/report` — aggregated Markdown + JSON
- `POST /sessions/{id}/run` — after submit, auto grade → diagnose → plan (demo helper)

### 7.2 Web

Streamlit four-step wizard: profile → answer → review grade/diagnosis → review plan. **HTTP to FastAPI only** (no duplicate business logic in the UI layer).

**UI bar (even in MVP):** clean, calm, education-appropriate — clear hierarchy, readable Chinese typography, soft academic color palette (avoid generic “AI purple” chrome), generous whitespace, progress that feels like a lesson flow rather than a dense admin dashboard. Visual polish is in-scope; flashy gamification is not.

### 7.3 CLI

- `ilearn run` — end-to-end session
- `ilearn eval` — minimal evaluation runner

## 8. Evaluation (Minimal)

- Primary: self-built step-grading set (10–30 fixtures: stem, student answer, expected tags / step correctness)
  - Metrics: error-tag macro-F1, final-correct accuracy, JSON validity rate
- Optional: small public subset related to error identification / feedback (e.g. BEA 2025 shared-task slice) if obtainable; otherwise document self-built-only
- Full EduAgentBench / multi-benchmark suite is **post-MVP**

## 9. Error Handling

- LLM/network failure → one retry → degrade and surface in report
- Assessment mix validation failure → refuse to emit paper
- Missing API key → CLI can run structural demo with fixtures (no live grading quality claims)

## 10. Non-Goals (MVP)

- VL / photo answers
- Multi-subject
- Live web curriculum retrieval
- Multi-turn Socratic tutoring
- Automatic path re-planning after every practice
- Teacher lesson-prep agents
- Class-level reports
- Real identifiable student PII

## 11. Success Criteria

1. Web and CLI complete the 20-item loop: profile → assess → answer → grade → diagnose → plan
2. `ilearn eval` runs repeatably and prints scores
3. Unit tests cover mix quotas and schema validation
4. Pilot provider is the only curriculum backend, behind a stable interface

## 12. Later Phases (Not This Spec)

1. Curriculum RAG / multi-region packs
2. VL grading
3. Multi-turn tutoring on top of step grades
4. Dynamic re-planning feedback loop
5. Broader public benchmark integration from `doc/evaluate.txt`

## 13. References (Project Docs)

- `doc/design_think.txt` — product hard requirements
- `doc/project.txt` — module inspiration
- `doc/open_source.txt` — projects to learn from (compose, don’t clone)
- `doc/evaluate.txt` — future eval landscape
