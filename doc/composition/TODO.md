# ILearn 未完成 ToDo 全清单

> **生成日期：** 2026-08-10  
> **最后更新：** 2026-08-10（Phase1 收尾验收）  
> **对照基线：** `master`（Composition Phase 1 收尾完成；177 tests）  
> **来源：** `OPTIMIZATION_BACKLOG.md`、`MULTI_AGENT_ARCHITECTURE.md`、`docs/superpowers` 计划/specs、`design_think.txt`、`evaluate.txt`、`INDEX.md`、Phase1 终审残留  
> **说明：** 只列**未完成 / 部分完成 / 完全未做**项；已完成项不收录。状态：`partial` = 有骨架未闭环；`open` = 完全未做。

---

## 0. 汇总

| 类别 | 数量 | 说明 |
|------|------|------|
| A. Phase1 P0 收尾 | 0 open | ✅ A-01…A-05 done（A-03 向量 Qdrant 延至 Phase 2c） |
| B. Backlog P1 | 18 | OPT-023…026 done Phase 2a |
| C. Backlog P2 | 8 | OPT-074 done Phase 2a |
| D. 架构 / Spec 延期能力 | 12 | 计划明示 Later |
| E. design_think / evaluate 缺口 | 14 | 产品硬需求与评测景观 |
| F. 文档 / 仓库运维 | 3 open | F-01…F-04 done；F-05…F-07 仍 open |
| G. 工程债 / 终审遗留 | 0 open | G-01…G-06 done（G-05 Phase 2a 2026-08-10） |
| **合计 open** | **55** | 去重后仍按条目全记；跨类引用用「见 xxx」 |

---

## A. Composition Phase 1 — P0 收尾 ✅（2026-08-10）

| ID | 标题 | 状态 | 缺口说明 | 建议验收 |
|----|------|------|----------|----------|
| A-01 / OPT-010 | StepAttempt / StepVerdict 协议 | **done** 2026-08-10 | PracticeAgent 写出 StepAttempt；与 rubric 对齐单测 | — |
| A-02 / OPT-022 | 五维画像 `contextual` | **done** 2026-08-10 | grade/region 写入 contextual；单测 | — |
| A-03 / OPT-040 | 课标 **向量** RAG | **done** 2026-08-10（keyword RAG） | keyword RAG + `curriculum_sources.json` 已落地；**向量 Qdrant 索引仍 open → Phase 2c** | Phase 2c：向量检索 + recall 单测 |
| A-04 / OPT-071 | tutor_gym completeness CLI | **done** 2026-08-10 | `ilearn eval --completeness` / `--tutor-gym` | — |
| A-05 / OPT-070 | mathtutorbench 子集不全 | **done** 2026-08-10 | `--mistake-correction`、`--scaffolding` CLI 已接入 | — |

---

## B. OPTIMIZATION_BACKLOG — P1（全部 open）

### B1. AssessmentAgent

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-002 | LLM 补题 + 历史去重 | 模板不足时 LLM 补题；follow-up 与 diagnostic 去重 | OPT-001 |
| OPT-003 | 分层作业配额模板（语文/多学科） | 基础/提高/拓展三层 + 题型约束；K12 多学科扩展 | 无 |
| OPT-004 | 结构化 Assessment Pydantic 增强 | choice/fill/constructed + rubric + cognitive_level | 无 |

### B2. PracticeAgent

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-013 | 错因四分类扩展 error_tags | conceptual/procedural/strategic/representational 映射或扩展 | 无 |
| OPT-014 | 动态三级 Hint Ladder | 按错因生成 hint；连续失败退出到讲解；不泄答案 | OPT-013 |
| OPT-015 | PendingQuestion 服务端答案绑定 | question_id 绑定 expected_answer，防跨轮串题 | 无 |

### B3. DiagnosisAgent

| ID | 标题 | 状态 | 说明 | 依赖 |
|----|------|------|------|------|
| OPT-023 | Evidence→Mastery 确定性更新 | **done** 2026-08-10 | 证据→星级/置信度/复习日；LLM 不直接改 mastery | OPT-021 |
| OPT-024 | Memory Graph 证据链（轻量） | **done** 2026-08-10 | claims 带来源 session/item/step；报告可引用 evidence_id | OPT-021 |
| OPT-025 | 结构化 WeaknessEvent | **done** 2026-08-10 | knowledge_id+step_id+error_tag+confidence；时间衰减 | OPT-021 |
| OPT-026 | Leech 连续失败识别 | **done** 2026-08-10 | N 次失败未掌握 → 干预优先级提升 | OPT-021 |

### B4. PlanningAgent

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-031 | 挫败感知 replan | 连续低分/高 hint → 降难度/回退前置/信心重建 | OPT-022, OPT-030 |
| OPT-032 | 计划 draft / approved / superseded | 重规划不覆盖旧计划；确认后发布 | 无 |
| OPT-033 | 三段式干预建议模板 | 当前认知 — 预测难点 — 教学方案 | OPT-025 |
| OPT-034 | KC 类型决定干预方式 | fact/skill/principle → 不同任务文案 | OPT-010 |

### B5. CurriculumAgent

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-041 | CurriculumCitation 绑定题目与报告 | 每题/每干预带 curriculum_objective_ids | OPT-040 |
| OPT-042 | Retriever 后端可替换 | local JSON / Qdrant 统一 retrieve 接口 | OPT-040 |

### B6. Orchestrator

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-050 | ContextOrchestrator 上下文预算 | profile + 滚动摘要 + token 预算 | OPT-022 |
| OPT-051 | 结构化 Agent 决策契约 | decision 含 reason + evidence_ids；可观测轨迹 | 无 |
| OPT-052 | Phase 级质量门 + 重试 | schema 失败 → 重试 1 次 → degrade | 无 |

### B7. Eval / Skills / 横切

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-072 | 评测隔离：提交冻结 + rubric 后读 | eval 不可改 fixtures；rubric 与模型输出分离 | 无 |
| OPT-073 | Skill Registry Top-20 回归 | 20 个 SKILL 输出 schema 快照测试 | 无 |
| OPT-081 | ILearn Skill Registry（本地） | pedagogical prompt 版本化注册；未知 id fail | OPT-073 |

---

## C. OPTIMIZATION_BACKLOG — P2（全部 open）

| ID | 标题 | 描述（摘要） | 依赖 |
|----|------|--------------|------|
| OPT-005 | Chapter DAG 先修关系 | 知识点 prerequisite 图 + 环检测 | OPT-010 |
| OPT-016 | Agent Capability 白名单 | 各 Agent 能力边界；越权 fail | 无 |
| OPT-027 | 会后异步 Profiler 钩子 | GRADE 后异步提取 logic_gap | OPT-025 |
| OPT-035 | 考试窗口驱动复习优先级 | 考试日期 → 计划压缩重点 | 无 |
| OPT-043 | Syllabus 进度范围护栏 | 组题/计划不超用户声明进度 | OPT-040 |
| OPT-053 | 入口意图层 | 规则优先 intent；LLM 仅模糊 NL | 无 |
| OPT-060 | **TutorAgent** 苏格拉底子状态机 | LOCATE_GAP→HINT→RETRY→EXPLAIN | OPT-014 |
| OPT-074 | practice–probe gap 指标 | **done** 2026-08-10：带提示 vs probe 差距超阈值 → flag | OPT-020 |
| OPT-082 | Explain→Quiz→Solve 前端向导 | Streamlit 三模式入口 | 无 |

---

## D. 架构 / Spec 明示延期（open）

来源：`MULTI_AGENT_ARCHITECTURE.md`、multi-agent-p0 plan Out of scope、MVP design §12、composition-audit-design。

| ID | 标题 | 来源 | 说明 |
|----|------|------|------|
| D-01 | TutorAgent 完整辅导环 | 架构 Phase 3 / OPT-060 | 多轮苏格拉底；与作业辅导产品线对齐 |
| D-02 | 动态重规划（复杂） | 架构 Phase 3 | 超出当前 consolidate loop；挫败 replan 见 OPT-031 |
| D-03 | LangGraph Director | 架构 §4 / multi-agent plan | 当前坚持 Python 状态机；Tutor 复杂后再议 |
| D-04 | 多地区课标包 | 架构 Phase 4 / design_think 5a | 非仅北京·人教；多 region packs |
| D-05 | 实时网页课标爬取 | multi-agent plan / README 非目标 | 网上最新公开教学资料拉取 |
| D-06 | EvalAgent 全基准 | 架构 Phase 4 | 超出 fixtures 适配器 |
| D-07 | EduAgentBench HF 导入 | multi-agent plan / evaluate.txt | Stage1/2 子集；公开数据集 |
| D-08 | VisionGradeResult 独立类型 | 架构 §5 | 现为 GradeResult 扩展字段；未拆独立 schema |
| D-09 | Agent `async run` 协议 | 架构 §5 示意 | 当前同步 `run`；未异步化 |
| D-10 | 多科目测评卷并行 | design_think §3「每个科目」 | 当前仅数学试点；K12 全科未开 |
| D-11 | 难度配额 50/40/10 与题型 40/40/20 | design_think §3/5b | 代码现为 10/8/2 题与 8/8/4（等价比例）；若产品要改比例需显式确认 | 备注：比例已对齐题数，若文案仍写百分比需文档统一 |
| D-12 | 教师端 / 班级报表 / PII | README 非目标 | 产品明确不做于当前版 |

> D-11：实现已用 20 题配额体现 50%/40%/10% 与 40%/40%/20%，**不算缺口**；若需改配额策略则另开任务。本清单保留为「文案/规格对齐」检查项。

---

## E. design_think / evaluate.txt 产品与评测缺口（open）

### E1. design_think 硬需求仍弱或未做

| ID | 标题 | 说明 |
|----|------|------|
| E-01 | 地区公开教学资料「最新」资源获取 | 5a：网上最新资源；现为静态 pilot JSON |
| E-02 | 学情能力维度细项 | 5d：逻辑/空间/心算等能力诊断仍偏知识点；能力 EMA 粗 |
| E-03 | 国家+地方教育要求双轨报告 | 5e：报告课标 citation 有，国家/地方双轨论证弱 |
| E-04 | 作业辅导作为独立产品能力 | §1「作业辅导」；现批改有、辅导会话（Tutor）无 |
| E-05 | K12 全学段数据与年级模型 | 定位 K12；年级 UI/schema 仍偏 4–6 |

### E2. evaluate.txt 公开基准（均未系统接入）

| ID | 基准 / 框架 | 状态 |
|----|-------------|------|
| E-10 | EduAgentBench | open（无 HF/任务导入） |
| E-11 | VeAgentBench | open |
| E-12 | ELMES | open |
| E-13 | KGCE | open |
| E-14 | AgentOS OpenLab | open |
| E-15 | TutorBench | open |
| E-16 | LEA 框架指标 | open |
| E-17 | BEA 2025 Shared Task | open |
| E-18 | MathTutorBench 全任务（非仅 mistake_location） | partial → 见 A-05 |
| E-19 | TutorGym 全领域（223 domains） | partial → 仅 completeness 采样 |
| E-20 | 规划类 ROUGE/BERTScore/NLI/LLM-as-Judge | open |
| E-21 | 辅导类 pedagogy_following 回归套件 | open（依赖 TutorAgent） |

---

## F. 文档 / composition 仓库运维

| ID | 标题 | 状态 | 说明 |
|----|------|------|------|
| F-01 | 刷新 `INDEX.md` 状态 | **done** 2026-08-10 | Phase1 收尾完成；指向 Phase 2a |
| F-02 | 刷新 `MULTI_AGENT_ARCHITECTURE.md` Phase 表 | **done** 2026-08-10 | §7 阶段表已更新 |
| F-03 | 刷新 `AGENT_MAPPING.md` | **done** 2026-08-10 | VL 已实现 |
| F-04 | 刷新 `ANALYSIS_BY_REPO_v2.md`「下一步」 | **done** 2026-08-10 | Phase1 done → Phase 2a |
| F-05 | hermes-edu-skills 拉取/调研 | open | INDEX：仓库未找到；npm 可选 |
| F-06 | xiaozhi-skills 克隆修复 | open | INDEX：网络/路径失败 |
| F-07 | EduGemma / AIFL / EduAgentBench / CAATS 澄清 | open | INDEX 待补充 URL 或排除；CAATS 同名误匹配已注明 |

---

## G. 工程债 / Phase1 终审与实现残留（G-05 → Phase 2a）

| ID | 标题 | 状态 | 说明 |
|----|------|------|------|
| G-01 | `datetime.utcnow()` 弃用警告 | **done** 2026-08-10 | 已迁移 timezone-aware |
| G-02 | evidence 重跑去重 | **done** 2026-08-10 | 同 session 再 grade 去重 |
| G-03 | OCR confidence 与 GradingReceipt 联动 | **done** 2026-08-10 | 图像路径 confidence/degraded 写入 receipt |
| G-04 | Blueprint fill 可复现 RNG | **done** 2026-08-10 | seed 接入两阶段填槽 |
| G-05 | 画像启发式偏薄 | **done** 2026-08-10 | `apply_from_evidence` 从 evidence_log 聚合 dimensions | OPT-023/024 |
| G-06 | `test_evidence_schemas` 未使用导入 | **done** 2026-08-10 | 移除未用导入；新增 `test_step_verdict_defaults` |

---

## H. 建议执行分组（非新任务，仅编排）

便于开下一阶段 writing-plans 时切包：

| 建议包 | 包含 ID | 目标 |
|--------|---------|------|
| **Phase1 收尾** ✅ | A-01…A-05, G-01…G-04, G-06, F-01…F-04 | **已完成** 2026-08-10（G-05 deferred Phase 2a） |
| **Composition Phase 2a（诊断/证据）** ✅ | OPT-023…026, OPT-074, G-05 | **已完成** 2026-08-10（198 tests） |
| **Composition Phase 2b（规划/辅导）** | OPT-014, OPT-031…034, OPT-060 | Hint + replan + Tutor |
| **Composition Phase 2c（课标/多科）** | A-03, OPT-041/042, OPT-003, D-04, E-05 | K12 扩展与 citation |
| **Composition Phase 2d（编排质量）** | OPT-050…052, OPT-015, OPT-016 | 预算/契约/质量门 |
| **Eval 扩展** | OPT-072/073/081, E-10…E-21 | 公开基准与 Skill |
| **文档刷新** | F-01…F-07 | 本地 composition 文档与仓库索引 |

---

## 附录：已完成（不纳入 ToDo，仅对照）

- MVP 管道；Multi-Agent P0（6 Agent + Orchestrator + VL 离线降级）
- Composition Phase 2a 诊断/证据：OPT-023…026、OPT-074、G-05（2026-08-10；198 tests）
- Composition Phase1 收尾：A-01…A-05、G-01…G-04/G-06、F-01…F-04（2026-08-10；G-05 → Phase 2a）
- Composition Phase1 主体：OPT-001/011/012/020/021/030/080；OPT-010/022/040/070/071
- README K12 定位 + REFERENCE 致谢 + eval CLI 新 flags
- 公开仓库 `master` 已推送

---

*本文件为活文档：完成一项请在对应行标注 `done` 与日期/commit，或移入「已完成」附录。*
