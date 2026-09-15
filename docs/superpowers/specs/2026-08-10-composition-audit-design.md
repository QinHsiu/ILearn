# Composition 深度审计设计 Spec

> **Status:** Approved (brainstorming 2026-08-10)  
> **Goal:** 对 `doc/composition/` 本地 24 个开源仓库进行标准深度审计，产出可执行的 ILearn 优化 backlog；**本阶段只写文档，不改代码**。  
> **Baseline:** `feature/ilearn-multi-agent-p0`（6 Agent + Orchestrator，125 tests）  
> **Aligns with:** `doc/design_think.txt`, `doc/think_p0.txt`

---

## 1. 背景与动机

### 1.1 现状

- **ILearn P0** 已实现显式多 Agent：Assessment / Practice / Diagnosis / Planning / Curriculum / Eval + `MultiAgentOrchestrator`。
- **composition/** 已克隆 **24** 个开源仓库；`ANALYSIS_BY_REPO.md` 为初筛（README + 核心文件概览），深度不足。
- **design_think.txt** 中多项能力仍为部分实现或缺失：课标 RAG、VL 手写质量、证据链诊断、公开基准、动态重规划、TutorAgent 等。

### 1.2 本轮交付（审计阶段）

| 产出 | 路径 | 说明 |
|------|------|------|
| 深度审计主报告 | `doc/composition/ANALYSIS_BY_REPO_v2.md` | 24 仓库 × 8 块 + synthesis |
| 优化 backlog | `doc/composition/OPTIMIZATION_BACKLOG.md` | 按 Agent 分类，P0/P1/P2 |
| 索引更新 | `doc/composition/INDEX.md` | 导航与版本说明 |

**不在范围：** 未克隆的 5 项（hermes、xiaozhi、EduAgentBench HF、EduGemma、AIFL）；`ilearn/` 代码改动。

---

## 2. 约束与原则

- **组合不抄袭：** 提炼模式与接口，不复制整仓代码。
- **对照基准：** 以当前 `ilearn/agents/*` 与 `design_think.txt` 为 gap 标尺。
- **YAGNI：** 审计结论区分「直接复用 / 需改造 / 仅参考」；不推动 LangGraph 全量迁移等过度工程。
- **本地文档：** `doc/`、`docs/` 为 gitignore，审计产物存 `doc/composition/`。

---

## 3. 审计方法论

### 3.1 每仓库阅读范围

1. README / 架构说明  
2. Agent 定义与编排入口（orchestrator / graph / loop / DAG）  
3. 组题 / 批改 / 诊断 / 规划相关核心模块  
4. 数据模型（schema、画像、掌握度、证据链）  
5. 评测与测试（若有）  

**不读：** 前端 UI 细节、部署脚本、与 K12 数学测评环无关的科目逻辑。

### 3.2 标准 8 块模板（每仓库 1–2 页）

| # | 章节 | 内容要求 |
|---|------|----------|
| 1 | 概览 | 定位、技术栈、成熟度（prototype / demo / production-ish） |
| 2 | 架构与编排 | 状态机 / LangGraph / ReAct / DAG / 管道 |
| 3 | Agent 角色 | 所有 Agent 及职责清单 |
| 4 | 数据模型 | 画像、掌握度、证据链、会话状态 |
| 5 | 组题能力 | 题源、约束、课标/难度/题型 |
| 6 | 批改与辅导 | 步骤批改、VL、错因、hint ladder |
| 7 | 学情与规划 | 诊断维度、计划生成、重规划触发 |
| 8 | ILearn 借鉴 | 每条：**直接复用 / 需改造 / 仅参考** + 目标 `ilearn/` 模块 |

附加：**不建议借鉴**（1 条，防误用）。

### 3.3 借鉴类型定义

| 类型 | 含义 |
|------|------|
| **直接复用** | 可移植 prompt、schema、评测脚本、SKILL.md 路径 |
| **需改造** | 核心思路可用，需适配 ILearn schema / 试点课标 / Agent 接口 |
| **仅参考** | 产品叙事或架构启发，无现成代码 |

---

## 4. 审计顺序（24 仓库）

按与 ILearn 终态相关度排序：

```
Batch 1 架构标杆
  1. LearnGraph
  2. DeepTutor
  3. WeSmartFlow
  4. ECNUClaw

Batch 2 四 Agent 直接对标
  5. Socratic-Education-System
  6. OpenMAIC
  7. StudyCoach
  8. ai-vocab-agent

Batch 3 评测与实验
  9. tutor_gym
  10. mathtutorbench
  11. ProMentor
  12. latent
  13. learn-pi

Batch 4 多 Agent 编排参考
  14. EduAgents
  15. Chinese-Teaching-AI-Agent
  16. Claw-ED
  17. AI-Shool-Counselor

Batch 5 画像与 LMS
  18. Personal-Canvas-Agent
  19. inno-agent
  20. LanguageMentor
  21. EduNex-Autonomous-AI-Tutor-for-Every-Student-Demo

Batch 6 技能库
  22. education-agent-skills
  23. OpenClaw-Education-Skills
  24. Dewey
```

---

## 5. 主报告结构（ANALYSIS_BY_REPO_v2.md）

```markdown
# ILearn 开源 Composition 深度审计 v2

## 0. 执行摘要
- Top-10 可借鉴模式
- P0 已覆盖 vs design_think 仍缺失
- 5 类反模式（不建议照搬）

## 1–24. 逐仓库审计（标准 8 块）

## 25. 跨仓库 Synthesis
  25.1 编排模式对比表
  25.2 组题模式对比表
  25.3 批改/辅导模式对比表
  25.4 学情/画像模式对比表
  25.5 规划/重规划模式对比表
  25.6 评测基准对比表
  25.7 技能库 Top-20 SKILL 路径

## 26. ILearn Gap Matrix（定稿）
```

---

## 6. Backlog 结构（OPTIMIZATION_BACKLOG.md）

### 6.1 分类

- AssessmentAgent（组题）
- PracticeAgent（练题/批改）
- DiagnosisAgent（学情诊断）
- PlanningAgent（学习建议）
- CurriculumAgent（课标）
- Orchestrator（编排/记忆）
- TutorAgent（待建，二期）
- EvalAgent（评测）
- 横切：数据模型 / UI / 基础设施

### 6.2 条目格式

```markdown
### OPT-001 [P0] AssessmentAgent: <标题>
- **来源:** DeepTutor / agents/question/
- **借鉴类型:** 需改造
- **目标文件:** ilearn/agents/assessment.py, ilearn/core/assessment.py
- **描述:** ...
- **验收:** pytest 通过 + 具体指标
- **依赖:** OPT-xxx 或 无
```

### 6.3 优先级

| 级别 | 定义 |
|------|------|
| **P0** | 阻塞 design_think 核心闭环（课标 RAG、批改质量、基准评测、重规划等） |
| **P1** | 显著提升质量/可解释性，不阻塞 demo |
| **P2** | 锦上添花（TutorAgent、LangGraph 可视化、多科目） |

---

## 7. Gap Matrix 预填（审计定稿时验证/修正）

| design_think 条款 | P0 现状 | 最佳借鉴源 | 优先级 |
|-------------------|---------|------------|--------|
| 地区课标 + 公开教学资源 RAG | 本地 JSON，无向量检索 | DeepTutor KB、ai-vocab-agent、WeSmartFlow KG | P0 |
| 20 题难度/题型配额 | ✅ MIX_BLUEPRINT | OpenMAIC、DeepTutor Question Bank | P1 |
| LLM 补题 + 课标 citation | ❌ | DeepTutor、OpenMAIC | P1 |
| 键盘 + VL 手写步骤批改 | ⚠️ VisionGrader 离线降级 | ai-vocab-agent、mathtutorbench | P0 |
| 步骤错因 → 能力诊断 | ⚠️ 5 error_tags + 启发式 | mathtutorbench、ECNUClaw | P1 |
| 知识点掌握等级 | ✅ mastered/unstable/weak | LearnGraph Evidence→Mastery | P1 |
| 多维学习者画像 | ⚠️ 简版 Portrait | ECNUClaw、WeSmartFlow | P0 |
| 证据链可追溯诊断 | ❌ | DeepTutor Memory Graph | P1 |
| 规划 + 国家/地方纲要 | ⚠️ 模板 + citation append | StudyCoach、education-agent-skills | P1 |
| 间隔复习 | ❌ | education-agent-skills spaced-practice | P1 |
| 练→评→练动态重规划 | ⚠️ loop≤2 规则触发 | LearnGraph、ECNUClaw replan | P0 |
| 苏格拉底辅导 | ❌ | Socratic、DeepTutor Mastery | P2 |
| 公开基准评测 | ⚠️ 自建 fixtures | tutor_gym、mathtutorbench | P0 |
| Orchestrator 上下文预算 | ❌ | WeSmartFlow ContextOrchestrator | P2 |
| Pedagogical SKILL 注册 | ❌ | education-agent-skills | P1 |

---

## 8. Top-10 优化方向（审计重点验证）

| # | 方向 | 主源 | 目标 |
|---|------|------|------|
| 1 | 课标向量 RAG + citation | DeepTutor + ai-vocab-agent | CurriculumAgent, AssessmentAgent |
| 2 | Evidence→Mastery 公式 | LearnGraph | DiagnosisAgent, LearnerPortrait |
| 3 | 五维/三维掌握度 | ECNUClaw + WeSmartFlow | DiagnosisAgent, schemas |
| 4 | mathtutorbench 错因 prompt | mathtutorbench | PracticeAgent, VisionGrader |
| 5 | tutor_gym 步骤评测 | tutor_gym | EvalAgent |
| 6 | Memory Graph 证据链 | DeepTutor | Diagnosis 扩展 / EvidenceStore |
| 7 | 间隔复习 | education-agent-skills | PlanningAgent |
| 8 | 挫败感知 replan | ECNUClaw | PlanningAgent, Orchestrator |
| 9 | Question Bank LLM 补题 | DeepTutor / OpenMAIC | AssessmentAgent |
| 10 | TutorAgent 三级 hint | Socratic + ProMentor | 新 TutorAgent (P2) |

---

## 9. 不建议借鉴（预清单，审计验证）

| 反模式 | 仓库 | 原因 |
|--------|------|------|
| 整仓 LangGraph 迁移 | OpenMAIC, EduAgents | ILearn 轻量 Orchestrator 已足够 |
| 前端 demo 无后端 | EduNex | 无 Agent 运行时 |
| 教师 PBL 备课流 | EduAgents, Claw-ED | 非学生测评环 |
| 纯概念 | Dewey | 无 executable |
| 392 skills 全量 | OpenClaw-Education-Skills | 精选 Top-20 |

---

## 10. 执行计划（审计工作本身）

### 10.1 工作量估算

- 24 仓库 × ~1.5 页 ≈ **36 页**主报告  
- Synthesis + Gap Matrix ≈ **6 页**  
- Backlog ≈ **40–60 条**（P0 约 8–12 条）  
- 合计 **~45 页** Markdown  

### 10.2 执行方式

1. 按 §4 顺序逐仓库审计，填充 8 块模板。  
2. 每完成 Batch，更新 synthesis 草稿中的对比表。  
3. 全部完成后写 §0 执行摘要与 Gap Matrix 定稿。  
4. 从 §8 与逐仓 §8 提炼 `OPTIMIZATION_BACKLOG.md`。  
5. 更新 `INDEX.md` 指向 v2 文档。

### 10.3 下一阶段（本 spec 之后）

- 用户审阅本 spec 与审计产出。  
-  invoke **writing-plans** → `docs/superpowers/plans/YYYY-MM-DD-composition-optimization.md`（按 P0 backlog 分批实施）。  
- **不在本 spec 范围：** 直接修改 `ilearn/` 代码。

---

## 11. 验收标准（审计阶段完成定义）

- [ ] `ANALYSIS_BY_REPO_v2.md` 含完整 24 仓库审计 + synthesis + Gap Matrix  
- [ ] 每仓库均有 8 块 +「不建议借鉴」  
- [ ] `OPTIMIZATION_BACKLOG.md` 含 P0/P1/P2 分类与 OPT-xxx ID  
- [ ] `INDEX.md` 已更新导航  
- [ ] 无 TBD/TODO 占位符  
- [ ] Top-10 方向与 Gap Matrix 一致  

---

## 12. Self-Review Checklist

- [x] 范围限定为 24 本地仓库，不含 external-only  
- [x] 交付路径与 brainstorming 对齐（主报告 + backlog + INDEX）  
- [x] 与 P0 代码 baseline 一致  
- [x] 优先级定义明确  
- [x] 审计与实现阶段分离  
- [x] 无内部矛盾（方案 1 顺序 + Agent 分类 backlog）
