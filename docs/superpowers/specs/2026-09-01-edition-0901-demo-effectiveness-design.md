# Edition 0901 Design — Demo Unit (小数乘法) + Teaching Effectiveness (C + C1)

**Date:** 2026-09-01  
**Status:** Ready for user review (self-reviewed)  
**Source:** `doc/edition_0901.txt` (full P0–P2, demo session mode **C1**)  
**Baseline:** Edition 0830_9 A2

## Goal

Deliver a judge-ready **K12 teaching-unit demo** for 人教·五年级「小数乘法」and a **teaching-effectiveness** stack (metrics, API, dashboard UI, PDF export), with one-click creation of a **fully pre-seeded closed-loop session** (paper → grades → diagnosis → plan + class demo metadata).

## Scope

**In (C / P0–P2):**

1. Demo unit data `math_5_1` + seed factory → complete `SessionState`
2. `POST /demo/units/{unit_id}/session` (+ optional teacher/parent bind)
3. `TeachingEffectivenessMetrics` + `compute_metrics`
4. `GET /sessions/{id}/effectiveness` + comparison payload
5. `GET /sessions/{id}/export/effectiveness.pdf` (MD → existing `markdown_to_pdf`)
6. Landing「体验完整教学单元」CTA + deep links
7. Teacher/Parent dashboard demo panels (class heatmap-style stats from `demo_class_data`, parent-friendly tips from enrichment)
8. `EffectivenessDashboard` React component
9. `scripts/generate_demo_effectiveness.py` → `data/demo/effectiveness_summary.json` fixture

**Out:**

- Unifying PDF engines / WeasyPrint-only
- Full react-router migration
- Runtime orchestrator auto-run to fill demo (non-deterministic)
- New subjects beyond math_5_1 in this edition
- Historical multi-session analytics DB (summary JSON fixture only)

## Architecture (approved §1)

**Approach:** Pre-seeded session factory + pure metrics service (sync), wired through FastAPI and existing dashboard/query deep links.

| Layer | Path | Responsibility |
| --- | --- | --- |
| Unit fixture | `data/demo/units/math_5_1.json` | Unit meta, blueprint, profile overrides, class demo stats, KP list |
| Seed | `ilearn/demo/units.py`, `ilearn/demo/seed.py` | Load unit; build SessionState (20 items, grades, diagnosis, plan, metadata) |
| API demo | `ilearn/api/demo.py` (or routes on `app.py`) | `POST /demo/units/{unit_id}/session` |
| Effectiveness | `ilearn/core/effectiveness.py` | Pydantic metrics + `compute_metrics(session)` + markdown report |
| API metrics | `ilearn/api/app.py` / dashboard router | GET effectiveness + export PDF |
| Script | `scripts/generate_demo_effectiveness.py` | Write summary fixture |
| Frontend | Landing, EffectivenessDashboard, Teacher/Parent panels, client | Demo CTA, KPI UI, role deep links |

### Demo session shape (C1)

After seed, session must validate as `SessionState` with:

- `profile`: 北京, grade 5, age 11, nickname 小明, gender male, subject math
- `phase`: `plan` (SessionPhase.PLAN)
- `paper`: **exactly 20** `AssessmentItem`s aligned to decimal-multiplication KPs (`dec_mult` and/or named skills in fixture); mix choice/fill/constructed per blueprint
- `answers` + `grades`: consistent with a mid-level learner (weak on 小数乘小数 / 运算律推广)
- `diagnosis`: knowledge_mastery + interventions; `metadata.diagnosis_enrichment` includes `parent_summary`, `teacher_summary`, `diagnosis_confidence`
- `plan`: goal/days/markdown focused on weak KPs
- `evidence_log`: ≥5 entries
- `metadata.demo_unit`: `"math_5_1"`
- `metadata.demo_class_data`: class_size, avg_mastery, mastery_distribution, common_weaknesses
- `metadata.parent_view_count` / `teacher_notes_count`: demo integers

Create also binds:

- parent `demo_parent` → session
- teacher `demo_teacher` / class `demo_class_5a` → session  

so existing dashboard APIs work with query  
`?login=1&role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=<sid>`  
(and parent analog).

### Effectiveness metrics

`TeachingEffectivenessMetrics` fields (computed, not all stored):

- Learning: `pre_assessment_score`, `post_assessment_score` (optional/None), `mastery_gain`, `weakness_resolved_count`, `weakness_remaining_count`
- Teacher workload: `total_questions`, `auto_graded_count`, `manual_review_count`, `estimated_grading_time_minutes`, `traditional_grading_time_minutes`, `time_saved_percent`
- Engagement: `session_duration_seconds` (from metadata or 0), `hint_used_count`, `avg_response_time_seconds` (metadata/0), `completion_rate`
- Diagnosis: `diagnosis_confidence`, `evidence_count`
- Home-school: `parent_view_count`, `teacher_notes_count`

**Formulas (deterministic):**

- `pre_assessment_score = 100 * correct(grades) / max(len(grades),1)`
- `auto_graded_count = count(not grade.grading_degraded)`; manual = rest (or constructed types as manual if preferred — pick one rule and test it: **degraded OR type==constructed → manual**)
- `traditional = total * 2.0`; `ilearn = manual * 1.0 + 0.5`; `time_saved_percent = (traditional-ilearn)/traditional*100`
- `completion_rate = 100 * len(answers) / max(len(paper.items),1)`
- `weakness_remaining = count(mastery.level == "weak")`; resolved from metadata `demo_weaknesses_resolved` (seeded int) when post score absent
- `mastery_gain = post - pre` if post else metadata `demo_mastery_gain` (seeded, e.g. 18.0) for demo narrative

Comparison payload (static traditional vs ILearn copy + live numbers).

### Frontend

- **Landing:** section + card for 小数乘法；button calls demo API；navigates via `window.location` / href to teacher link (primary) with secondary links for parent/student
- **EffectivenessDashboard:** four MetricCards + comparison table + export button
- **TeacherDashboard:** when selected detail has `metadata.demo_unit`, show 备课概览 / 班级分布 / workload from metrics API
- **ParentDashboard:** when demo session, show parent_summary + parent tips from enrichment / plan
- Preserve existing bind/list flows; demo is additive

## Data flow / errors / tests (approved §2)

### Data flow

Landing → POST demo session → seed+save+bind → links → role surfaces → effectiveness GET/PDF.

### Errors

| Case | HTTP / behavior |
| --- | --- |
| Unknown unit | 404 |
| Missing session for effectiveness/PDF | 404 |
| Seed validation error | 500; no partial save |

### Tests

| Area | Coverage |
| --- | --- |
| Seed | 20 items; phase plan; metadata keys; pydantic validate |
| Demo API | create 200; unknown 404; GET session works |
| Effectiveness | formula unit tests; API JSON shape; PDF non-empty bytes |
| Frontend | Landing CTA mock; EffectivenessDashboard render; sessionStep-style pure helpers if any |

### Implementation task order

1. Fixture + seed + demo POST  
2. effectiveness core + GET  
3. PDF export + summary script  
4. Landing CTA + client  
5. Dashboard panels + EffectivenessDashboard  
6. VERSION.md Edition 0901  

## Success criteria

- [ ] One-click demo creates offline-complete session for math_5_1
- [ ] Teacher/parent deep links show populated demo panels
- [ ] Effectiveness API + PDF work without LLM
- [ ] Pytest + vitest green; VERSION notes Edition 0901
