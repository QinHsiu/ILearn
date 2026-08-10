# VERSION

ILearn 当前版本说明：定位、本版范围、更新记录与近期 Todo。  
详细未完成清单见本地 `doc/composition/TODO.md`（若存在）。

| | |
| --- | --- |
| **标签** | Composition Phase 2c（课标 / 多科）已合入 `master` |
| **基线** | 258 tests（离线可跑） |
| **日期** | 2026-08-10 |

---

## 定位

面向 **K12 全学段** 的学情诊断与个性化学习规划多 Agent 系统（多学科可扩展）。

一次测评 → 分步批改 → 精准诊断 → 课标对齐的学习计划 → 薄弱点巩固闭环。

---

## 本版范围（已落地 · 试点）

- **试点学科 / 学段：** 小学数学（四至六年级）；建档 UI 支持年级 1–12，试点 provider 对 4–6 外年级 fail closed
- **试点课标：** 北京·人教（`data/pilot/`）；上海·人教 citation stub（`data/pilot/regions/shanghai_renjiao/`）
- **核心闭环：** 分步批改、错误标签、学情 Top-N、学习者画像、1–2 周计划、巩固环（`loop_count` ≤ 2）
- **Phase 2a：** Evidence→Mastery、WeaknessEvent、leech、evidence_id、practice–probe gap、画像从证据聚合
- **Phase 2b：** Hint Ladder、挫败感知 replan、计划 draft/superseded、三段式干预、KC 类型任务、TutorAgent 骨架
- **Phase 2c：** `CurriculumRetriever`（keyword / hash_vector / Qdrant stub）、按题 citation 绑定、语文配额 stub、多地区 source packs、`ILEARN_RETRIEVER_BACKEND`
- **工程面：** FastAPI + Streamlit + CLI；会话 JSON；OpenAI 兼容 LLM（可选）

---

## 更新日志

| 阶段 | 要点 | 测试 |
| --- | --- | --- |
| Multi-Agent P0 + Composition Phase 1 | 6 Agent 编排、ItemGrader / GradingReceipt、课标 keyword RAG、评测 CLI | 177 |
| Phase 1 收尾 | StepAttempt、contextual 画像、citation ids、completeness CLI 等 | 177 |
| Phase 2a 诊断 / 证据 | OPT-023…026、OPT-074、G-05 | 198 |
| Phase 2b 规划 / 辅导 | OPT-014、OPT-031…034、OPT-060 | 234 |
| Phase 2c 课标 / 多科 | A-03、OPT-041/042、OPT-003、D-04、E-05 → 合入 `master` 并 push | **258** |

---

## 近期 Todo

下一优先包（摘要；完整 ID 见 `doc/composition/TODO.md` §H）：

| 包 | 包含 | 目标 |
| --- | --- | --- |
| **Phase 2d（编排质量）** | OPT-050…052、OPT-015、OPT-016 | context 预算、决策契约、质量门、PendingQuestion、能力白名单 |
| **Eval 扩展** | OPT-072/073/081、E-10…E-21 | 公开基准与 Skill registry |
| **文档 / 仓库运维** | F-05…F-07 | hermes / xiaozhi / EduGemma 等研究与索引刷新 |

完成一项后：在本文件「更新日志」追加一行，并视需要上调基线测试数。
