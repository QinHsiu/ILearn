# ILearn 多 Agent 架构设计（对齐 design_think.txt）

> 基于 `doc/composition/` 24+ 开源项目分析 + 现有 MVP（`ilearn/` 管道）。  
> 原则：**不造轮子** — 编排与状态自研，能力模块借鉴开源；**组合不抄袭**。

---

## 1. 产品目标（来自 design_think.txt）


| 要求   | 说明                                                    |
| ---- | ----------------------------------------------------- |
| 正反馈环 | 练 → 评估&反馈 → 练（类强化学习，掌握度驱动下一练）                         |
| 冷启动  | 地区 + 年级 + 年龄 → 每科测评卷                                  |
| 卷面结构 | 20 题；难度 50/40/10；题型 40/40/20（选择/填空/解答）                |
| 作答   | 键盘 + **手写图片（VL 步骤批改）**                                |
| 批改   | **步骤级** + 错因标签                                        |
| 诊断   | 知识点薄弱 + 能力维度（逻辑/空间/心算等）+ 当地课标                         |
| 输出   | 个性化学习规划报告（国家 + 地方纲要）                                  |
| 质量   | 公开基准评测（tutor_gym / mathtutorbench / EduAgentBench 子集） |


---

## 2. Agent 全景（7 Agent + 1 Orchestrator）

```
                    ┌─────────────────────────────────────┐
                    │     Orchestrator（会话总线）          │
                    │  路由 · 状态机 · 记忆 · 工具注册      │
                    └─────────────────────────────────────┘
           ┌────────┬────────┬────────┬────────┬────────┬────────┐
           ▼        ▼        ▼        ▼        ▼        ▼        ▼
    Curriculum  Assessment  Practice  Diagnosis  Plan   Tutor   Eval
    Agent       Agent       Agent     Agent      Agent  Agent   Agent
    (课标RAG)   (组题)      (练题批改) (学情)     (建议) (辅导)  (评测)
```



### 2.1 四大核心 Agent（用户指定）



#### A. 组题 Agent — `AssessmentAgent`

**职责：** 根据地区、年级、年龄、科目，生成符合课标与卷面约束的测评/练习。


| 模块                 | 说明                                   | 借鉴来源                                          |
| ------------------ | ------------------------------------ | --------------------------------------------- |
| CurriculumProvider | 地区课标/纲要 RAG（MVP：试点 JSON → 二期：爬虫+向量库） | WeSmartFlow KG、DeepTutor KB                   |
| TemplateEngine     | 模板填槽 + 难度/题型配额（10/8/2, 8/8/4）        | MVP `AssessmentBuilder`                       |
| LLM ItemWriter     | 模板不足时 LLM 补题（强 schema + 课标 citation） | OpenMAIC quiz-content、DeepTutor deep_question |
| Validator          | 答案在选项内、知识点合法、配额校验                    | MVP fail-closed + tutor_gym 思路                |


**输入：** `StudentProfile`, `subject`, `paper_type=diagnostic|practice`  
**输出：** `AssessmentPaper`（含 rubric_steps）

---



#### B. 练题 Agent — `PracticeAgent`

**职责：** 接收作答（文本 / 图片），输出步骤级批改与错因；可选进入苏格拉底辅导子模式。


| 模块               | 说明                       | 借鉴来源                                  |
| ---------------- | ------------------------ | ------------------------------------- |
| TextGrader       | 客观题规则 + 解答 LLM 对齐 rubric | MVP `StepGrader`                      |
| VisionGrader     | 手写 OCR/VL → 步骤结构化 → 逐步判分 | ai-vocab-agent vision、EduGemma 思路     |
| ErrorTagger      | 受控错因词表 + 步骤评语            | mathtutorbench mistake_*              |
| TutorMode（可选）    | 三级 hint，不给最终答案           | Socratic Tutor、education-agent-skills |
| VariationGen（环内） | 错题同考点变式 1–3 题            | design_think + DeepTutor followup     |


**输入：** `AssessmentItem`, `StudentAnswer(text|image)`  
**输出：** `GradeResult[]`（含 `step_results`, `error_tags`, `grading_degraded`）

---



#### C. 学情诊断 Agent — `DiagnosisAgent`

**职责：** 聚合批改结果，结合课标与能力模型，输出可追溯诊断报告。


| 模块                | 说明                     | 借鉴来源                                      |
| ----------------- | ---------------------- | ----------------------------------------- |
| MasteryAggregator | 知识点掌握率 + 等级（掌握/不稳/薄弱）  | LearnGraph Evidence→Mastery               |
| AbilityScorer     | 逻辑/空间/心算等（启发式 + 可解释）   | ECNUClaw 五维（简化为 ILearn 能力集）               |
| ProfilerHook      | 会话级 weakness_log 追加    | Socratic Profiler                         |
| PortraitUpdater   | 长期学习者画像增量更新            | ECNUClaw profile、WeSmartFlow Graph Memory |
| ReportBuilder     | 热力图、雷达、Top-N 干预、课标依据声明 | MVP `Diagnoser` + ECNUClaw assessment     |


**输入：** `GradeResult[]`, `AssessmentPaper`, `StudentProfile`, `LearnerPortrait?`  
**输出：** `DiagnosisReport`（含 `knowledge_mastery`, `ability_scores`, `interventions[Top5]`）

---



#### D. 个性化学习建议 Agent — `PlanningAgent`

**职责：** 依据诊断 + 地区纲要 + 可用时间，生成可执行的周/日计划；练习后触发重规划。


| 模块             | 说明                  | 借鉴来源                                   |
| -------------- | ------------------- | -------------------------------------- |
| GoalDecomposer | 1–2 周目标 → 里程碑       | StudyCoach studyplan                   |
| DailyScheduler | 日任务（复习点/练习量/自测）     | MVP `Planner`                          |
| SpacedReview   | 间隔复习插入              | education-agent-skills spaced-practice |
| ReplanTrigger  | 连续偏离预期 → 重规划        | LearnGraph Action、ECNUClaw replan      |
| ReportRenderer | Markdown + JSON 双输出 | MVP `LearningPlanReport`               |


**输入：** `DiagnosisReport`, `daily_minutes`, `CurriculumContext`  
**输出：** `LearningPlanReport`

---



### 2.2 补充 Agent（建议实现）


| Agent               | 职责                                           | 借鉴                                |
| ------------------- | -------------------------------------------- | --------------------------------- |
| **CurriculumAgent** | 地区课标抓取、清洗、索引、纲要问答                            | WeSmartFlow、Hermes 教材同步 skill     |
| **TutorAgent**      | 多轮苏格拉底辅导（非测评态）                               | Socratic、DeepTutor Mastery        |
| **EvalAgent**       | 离线跑 tutor_gym / mathtutorbench / 自建 fixtures | tutor_gym、mathtutorbench、MVP eval |


---



## 3. Orchestrator：正反馈状态机

借鉴 **LearnGraph G-R-E-M-A** + MVP `Orchestrator`，显式状态：

```
ONBOARD → ASSESS → PRACTICE → GRADE → DIAGNOSE → PLAN → (PRACTICE' → …)
```


| 状态        | 触发 Agent                | 持久化                                     |
| --------- | ----------------------- | --------------------------------------- |
| ONBOARD   | —                       | `StudentProfile`, `LearnerPortrait` 初始化 |
| ASSESS    | AssessmentAgent         | `AssessmentPaper`                       |
| PRACTICE  | —                       | `StudentAnswer[]`                       |
| GRADE     | PracticeAgent           | `GradeResult[]`                         |
| DIAGNOSE  | DiagnosisAgent          | `DiagnosisReport`, 更新 Portrait          |
| PLAN      | PlanningAgent           | `LearningPlanReport`                    |
| PRACTICE' | AssessmentAgent（薄弱点变式卷） | 新一轮 paper                               |


**Orchestrator 职责（不单 Agent）：**

- 会话 ID、阶段转换、降级策略（LLM 不可用）
- 调用 **education-agent-skills** 中的流程 prompt（形成性评价环）
- 写入 **Memory**：Portrait + weakness_log + 掌握度时序

---



## 4. 与现有 MVP 的演进路径


| MVP 模块              | 升级为 Agent          | 改动要点                                    |
| ------------------- | ------------------ | --------------------------------------- |
| `AssessmentBuilder` | AssessmentAgent    | 拆 CurriculumProvider RAG；LLM ItemWriter |
| `StepGrader`        | PracticeAgent      | 拆 VisionGrader；TutorMode                |
| `Diagnoser`         | DiagnosisAgent     | PortraitUpdater；ProfilerHook            |
| `Planner`           | PlanningAgent      | ReplanTrigger；SpacedReview              |
| `Orchestrator`      | Orchestrator + 状态机 | 显式 Agent 接口；事件总线                        |


**推荐编排技术（二期选一）：**

1. **轻量：** 保留 Python 管道 + Agent 接口类（与 MVP 一致，YAGNI）
2. **标准：** LangGraph StateGraph（借鉴 OpenMAIC Director）
3. **重型：** DeepTutor 式 LoopHost + Capability 插件

建议：**Phase 2 仍用管道 + Agent Protocol**；Phase 3 再引入 LangGraph（当 Tutor 多轮与重规划复杂化）。

---



## 5. 数据与接口（Agent 间契约）

沿用 MVP Pydantic schema，扩展：

```python
# Agent 统一接口（示意）
class Agent(Protocol):
    name: str
    async def run(self, ctx: SessionContext) -> AgentResult: ...

# SessionContext 携带
# profile, paper, answers, grades, diagnosis, plan, portrait, curriculum_label
```

**关键新增：**

- `LearnerPortrait`（长期）：借鉴 ECNUClaw 五维，ILearn 简化为 `knowledge_state` + `ability_ema` + `weakness_log[]`
- `CurriculumCitation`：组题/诊断/计划中的课标条目引用 id
- `ImageAnswer` + `VisionGradeResult extends GradeResult`

---



## 6. 评测策略（EvalAgent）


| 层级  | 工具                               | 指标             |
| --- | -------------------------------- | -------------- |
| 单元  | pytest                           | schema、配额、规则批改 |
| 批改  | 自建 fixtures + mathtutorbench 子任务 | 步骤 F1、错因 F1    |
| 辅导  | tutor_gym 采样                     | 动作准确率          |
| 端到端 | EduAgentBench Stage1/2 子集        | 教学判断、多轮辅导      |


---



## 7. 实施阶段建议


| 阶段                 | 交付                                              | 周期感        |
| ------------------ | ----------------------------------------------- | ---------- |
| **Phase 1** ✅      | MVP 管道 + Multi-Agent P0 + Composition P0 收尾      | 已完成（2026-08-10） |
| **Phase 2a** ✅      | 证据→掌握度闭环（OPT-023…026、OPT-074）                  | 已完成（2026-08-10） |
| **Phase 2b** ✅      | Hint + replan + TutorAgent 骨架（OPT-014/031…034/060） | 已完成（2026-08-10） |
| **Phase 2c**（下一步） | 课标向量 RAG（Qdrant）+ citation + K12 扩展              | 3–4 周      |
| **Phase 3**        | TutorAgent 完整辅导环 + 动态重规划                         | 6–8 周      |
| **Phase 4**        | EvalAgent 全基准 + 多地区课标                            | 持续         |


---



## 8. 文件落地建议（ILearn 仓库）

```
ilearn/
  agents/
    orchestrator.py      # 状态机 + 调度
    assessment.py        # 组题 Agent
    practice.py          # 练题 Agent
    diagnosis.py         # 学情 Agent
    planning.py          # 建议 Agent
    curriculum.py        # 课标 Agent（RAG）
    tutor.py             # 辅导 Agent（Phase 2b 骨架）
    eval_runner.py       # 评测 Agent
  core/                  # 现有 schemas、report（保留）
  providers/             # LLM、CurriculumProvider
```

本地设计文档继续放在 `doc/composition/`（不上传 GitHub）。