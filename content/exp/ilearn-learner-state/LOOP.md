# /exp_loop — ilearn-learner-state

## Round 0
- analysis: session event_log append-only without projection; StudentProfile session-scoped
- plans: implement user architecture P0→P3 (skip P4 wiki)
- chosen: LearnerState + store + SM-2 scheduler + ExperienceStore + TemplateRegistry
- evaluation: 13/13 dedicated tests pass; hash chain deterministic via event.occurred_at
- decision: **stop** — P0–P3 acceptance met
