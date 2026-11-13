# target_score — Learner State Architecture P0–P3

```yaml
experiment_id: ilearn-learner-state
gates:
  - pytest tests/test_learner_state_p0.py  # cross-session same hash
  - pytest tests/test_scheduler_p1.py      # SM-2 receipts
  - pytest tests/test_experience_p2.py     # experience_refs
  - pytest tests/test_template_registry_p3.py
  - pytest tests/test_orchestrator_learner_state.py
```
