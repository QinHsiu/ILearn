# Composition ToDo Roadmap (from TODO.md)

> **Not an implementation plan.** Indexes how `doc/composition/TODO.md` (~75 items) splits into executable writing-plans packages.  
> **Baseline:** `master`, ~165 tests.  
> **Source of truth for status:** `doc/composition/TODO.md`

## Scope decision

`TODO.md` spans independent subsystems. Per writing-plans skill, **do not** implement all 75 items in one plan. Use one plan per package below.

| Package | Plan file | Covers TODO §§ | Status |
|---------|-----------|----------------|--------|
| **Phase1 收尾** | [`2026-08-10-composition-phase1-closeout.md`](./2026-08-10-composition-phase1-closeout.md) | A + G (+ F-01..04 文档刷新) | **本会话已写计划** |
| Phase 2a 诊断/证据 | *(pending writing-plans)* | OPT-023…026, OPT-024, OPT-074 | 未写 |
| Phase 2b 规划/辅导 | *(pending)* | OPT-014, OPT-031…034, OPT-060 | 未写 |
| Phase 2c 课标/多科 | *(pending)* | A-03 向量/Qdrant 余量, OPT-041/042, OPT-003, D-04, E-05 | 未写 |
| Phase 2d 编排质量 | *(pending)* | OPT-050…052, OPT-015, OPT-016 | 未写 |
| Eval 扩展 | *(pending)* | OPT-072/073/081, E-10…E-21 | 未写 |
| 文档/仓库运维余量 | *(pending / 手工)* | F-05…F-07 | 未写 |

## Explicitly deferred outside closeout

- **Qdrant / 真·向量索引** → Phase 2c（closeout 只做 citation_id + 不可变 hash 验收补齐）
- **TutorAgent / LangGraph / 多地区爬取** → Phase 2b / D 类
- **公开 HF 全基准导入** → Eval 扩展包

## How to continue

1. Execute closeout plan (Subagent-Driven or Inline).  
2. Invoke `/writing-plans` again naming the next package (e.g. `TODO.md §H Phase 2a`).  
3. After each package, tick rows in `TODO.md`.
