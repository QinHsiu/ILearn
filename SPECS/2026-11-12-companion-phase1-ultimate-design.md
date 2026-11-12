# Companion Phase-1 Ultimate — Plan + Predict + Stage Packs

**Date:** 2026-11-12  
**Status:** Shipped — Phase-1 ultimate gates green (`content/exp/ilearn-companion-phase1/`)  
**Parent:** `SPECS/2026-11-12-lifelong-companion-ask-answer-design.md`

## Ultimate acceptance (Phase-1 education)

1. Five capabilities real (not stubs): Ask / Answer / Plan / Predict / Evaluate  
2. LifeStage routing primary → graduate with pack or honest degradation  
3. Host state machine + rails retained; offline path works  
4. `/exp_loop` gates in `content/exp/ilearn-companion-phase1/` all pass  
5. Frontend companion can surface plan/predict replies

## P2 Plan

- Offline week schedule (Mon–Sun slots) from diagnosis weak skills **or** stage defaults  
- Persist `session.metadata["companion_week_plan"]`  
- Action `{ type: "open_week_plan" }`  
- If no evidence: schedule + CTA to Evaluate (not a stub refusal)

## P2 Predict

- Risk score from `MasteryPublicView.probe_gap_count`, weak mastery, loop_count  
- Levels: `low | medium | high` + plain-language Chinese reply  
- Action `{ type: "suggest_evaluate" }` when high/medium without recent paper

## Stage packs (thin)

- `packs/b2_senior_high_math`, `b3_undergrad_math`, `b4_graduate_study` curriculum_sources  
- Companion grades: 4–12; life_stage override for undergrad/graduate via profile.life_stage  
- Assessment still PILOT 4–6 with graceful degrade

## Non-goals

- Full calendar sync / push notifications  
- Career / elder content (hooks only)  
- Replacing PlanningAgent pipeline — Companion Plan is a chat-facing week view that may cite `session.plan` when present
