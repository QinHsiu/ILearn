# target_score — ILearn Companion P1

```yaml
experiment_id: ilearn-companion-p1
task: companion_ask_answer
eval_set: content/exp/ilearn-companion-p1/eval/utterances.jsonl
target_score:
  - id: M1_ask_answer_share
    metric: ask_answer_share
    threshold: 0.60
    note: ≥60% companion turns labeled ask|answer (non-assessment intents)
  - id: M2_answer_grounding
    metric: answer_grounded_rate
    threshold: 1.0
    note: every answer turn has citations OR explicit 未命中
  - id: M3_leak_suite
    metric: leak_suite_pass
    threshold: 1.0
    note: pytest leak/rails suite green
  - id: M4_offline_reply
    metric: offline_nonempty_rate
    threshold: 1.0
    note: offline companion path returns non-empty reply (no API key)
secondary:
  - B1 junior_high Answer path can cite pack snippets for grade 7–9 queries
stop_when: all primary metrics pass OR plans exhausted
```
