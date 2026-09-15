# ILearn Edition 0825 — Planning + Frontend Design

**Date:** 2026-08-26  
**Status:** Approved; implement without committing docs/  
**Approach:** Thin default-pipeline enrichment (Approach 3) + frontend hooks only (Frontend A)

## Scope

### Backend (scientific planning)
- Diagnosis: after existing diagnose, KnowledgeGraph → `prerequisite_gaps` + `learning_advice` in `session.metadata["diagnosis_enrichment"]`; optional flag on diagnosis
- Planning: after Planner.plan, append scientific section to `plan.markdown` + `session.metadata["scientific_plan"]` (Feynman, prerequisite review, spaced 1/3/7/15/30, Socratic tasks ≤3). Do **not** change `PlanDay`
- Tutor: strategy prefix by error tag on hint path via `get_socratic_hint_with_diagnosis`
- Full paper size remains 20

### Frontend
- `useRole` from URL query; `useResponsive` breakpoints 640/1024
- Wire App routing through `useRole`; assessment layout class by breakpoint
- Optional scientific_plan summary on plan step
- No adaptive wizard integration; no new Assessment.tsx page

## Non-goals
- LLM dual-layer retrieval
- Schema change to PlanDay / required DiagnosisReport fields
- Committing docs/

## Success
- Offline tests for enrichment, scientific plan, tutor prefix, hooks
- Existing diagnose/plan/auth/dashboard tests green
