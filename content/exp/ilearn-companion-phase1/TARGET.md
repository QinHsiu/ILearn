# target_score — Companion Phase-1 Ultimate

```yaml
experiment_id: ilearn-companion-phase1
task: five_capabilities_education_window
eval_set: content/exp/ilearn-companion-phase1/eval/suite.jsonl
target_score:
  - id: C1_five_intents_live
    metric: five_intents_ok
    threshold: 1.0
  - id: C2_plan_has_week
    metric: plan_week_ok
    threshold: 1.0
  - id: C3_predict_has_risk
    metric: predict_risk_ok
    threshold: 1.0
  - id: C4_stage_packs
    metric: stage_pack_cite_rate
    threshold: 0.75
  - id: C5_p1_regression
    metric: p1_eval_pass
    threshold: 1.0
  - id: C6_leak_suite
    metric: leak_suite_pass
    threshold: 1.0
stop_when: all gates pass
```
