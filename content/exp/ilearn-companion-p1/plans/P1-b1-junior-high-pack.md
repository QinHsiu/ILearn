# P1 — B1 junior-high math pack stretch

- hypothesis: Loading grade 7–9 curriculum_sources via `data/pilot/packs/b1_junior_high_math/` lets Companion Answer cite snippets for junior_high queries without expanding assessment PILOT_GRADES.
- target_subset: utterances u12–u14 (grade 7 answer)
- expected_gain: citations ≥ 1 on ≥2/3 junior_high answer turns
- min_clear_gain: citation rate 0 → ≥0.66 on subset
- global_max_drop: primary M1–M4 must stay pass
- source: SPECS/2026-11-12-lifelong-companion-ask-answer-design.md §3 B1 / §9

## 数据侧
- Add pack curriculum_sources for 有理数 / 一元一次方程 / 整式加减
- Teach `load_curriculum_sources` to merge `packs/*/curriculum_sources.json`

## 模型侧
- N/A (rule+keyword RAG)

## 训练侧
- N/A
