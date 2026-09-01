# VERSION

ILearn 当前版本说明：定位、本版范围、更新记录与近期 Todo。  
详细未完成清单见本地 `doc/composition/TODO.md`（若存在）。

| | |
| --- | --- |
| **标签** | Edition 0901_2 学生摘要 + 计划步面板 |
| **基线** | 554 tests（离线可跑）+ 71 vitest |
| **日期** | 2026-09-01 |

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
- **Phase 2d：** 轻量上下文预算、结构化决策日志、阶段质量门、PendingQuestion 答案绑定、Agent 写能力白名单
- **工程面：** FastAPI + Streamlit + CLI；会话 JSON；OpenAI 兼容 LLM（可选）
- **Edition 0813 P0：** `StudentProfile` 昵称 / 性别；Streamlit 六套 CSS 主题（性别 × 学段）；例题库 `source_refs` 绑定与诊断报告 / UI 来源追溯
- **Edition 0813 P1：** 四维题目验证器（可解 / 现实 / 可读 / 情境）+ 单次修订；情境兴趣 `situation_interest` 双轨评估；`learning_difficulty` 巩固环扩展至 4 轮
- **Edition 0815：** Math-Verify、Guard 多级检测、CitationPanel、主题 token 增强
- **Edition 0815_e1：** 测评步 60 分钟倒计时、题干启发式可视化、专注模式文本辅导（复用 tutor API，每题≤3 次 HintInteraction）
- **PDF 导出：** 学习计划页一键导出做题复盘 / 学习报告 PDF（后端 MD→PDF；WeasyPrint 优先、fpdf2 回退；章节结构对齐 `doc/deepseek_edition/report.txt`）
- **Edition 0825（冷启动 · 后端）：** 进度映射 `ProgressMapper` + `data/curriculum/progress_mapping.json`；知识图谱 `KnowledgeGraph` + `data/knowledge_graph.json`；锚点卷（可变长）→ 完整诊断卷（仍为 **20** 题，配额不变）；API `POST /sessions/{id}/assessment/adaptive/start|continue`；Orchestrator 钩子；本地题库优先，Layer2 可 LLM/stub 补题
- **Edition 0825（规划 + 前端）：** 诊断默认写入 `metadata.diagnosis_enrichment`（前置缺口 + 学习建议）；规划追加「科学学习方法」至 `plan.markdown` + `metadata.scientific_plan`（费曼 / 间隔复习 / 苏格拉底任务，**不改 PlanDay**）；Tutor hint 按错误类型加策略前缀；前端 `useRole` / `useResponsive`，测评布局断点 class，计划页科学方法摘要
- **Edition 0825（双层检索 + Assessment 页）：** 锚点本地不足时 Layer2（LLM 或确定性 stub）；`frontend/src/pages/Assessment.tsx` 替换学生向导第 2 步（锚点→完整 20 题）；完整卷配额不变
- **Edition 0826（课标数据扩充）：** `ilearn/data/build_pilot.py` 统一重建管线；RCAE / MM-K12 / TAL-SCQ5K / **templates** 导入；知识点 **13 → 1294**（RCAE）；legacy 13 kp 例题 **≥8/个**（MM-K12 + TAL 中文 + 模板变式）；`data/pilot/ATTRIBUTION.md`
- **Edition 0827（多模态课标绑定）：** `CurriculumRef` + `CurriculumGate`；独立 `multimodal_bank.json`（不并入 `example_bank`）；MV-MATH 导入（bindings crosswalk + Channel B 中文题干）；锚点卷 **2–4** 道多模态、完整卷 **≤4** 道（仍为 **20** 题）；`GET /pilot-assets/{path}`；前端 `Assessment.tsx` 题干配图 + 章节横幅
- **Edition 0830（认知层次 + 风格 + 几何）：** `CognitiveSkillGraph`（分数三单元 ≥30 技能点）+ 诊断根因 enrichment；`LearningStyleInferer` + Planning 材料适配；JSXGraph `DynamicGeometryQuestion` + `PracticeAgent.analyze_geo_interaction`；`scripts/export_processed_bank.py` 导出清洗题库
- **Edition 0830_2 A（平台硬化）：** `ILearnSettings`；同步日志/`RetryHandler`；图谱 JSON 进程缓存；滑动窗口限流中间件；submit 入参校验（允许空答案）
- **Edition 0830_3 B（可靠性）：** `SessionStore` 线程锁+读缓存；按会话 `RLock`；LLM fallback/`RetryHandler`；诊断/规划空数据边界；`GraphValidator` 环依赖检测
- **Edition 0830_4 C（产品友好化）：** 家长/教师摘要；`error_attribution`；技能干预库增强 Tutor；Orchestrator 耗时日志
- **Edition 0830_5 D（可解释 + 分层干预）：** SessionStore 按会话锁；LLM fallback 深度护栏；认知图谱环依赖硬失败；`DiagnosisExplainer`/`unknown_skills`；分层干预；报告解释段
- **Edition 0830_6 D（置信度 + 提示闭环）：** KP 图谱环检测（默认告警/`strict_cycles` 硬失败）；`diagnosis_confidence`；`solved_after_hint` 回写；Tutor 挫败语气；提示效果摘要
- **Edition 0830_7 D（状态机 + 能力透明）：** `PhaseGuard`/`phase_history`；`FeatureRegistry` + `GET /capabilities`；`UserFriendlyError` 错误码
- **Edition 0830_8（缺口收口）：** 数学 `SubjectAdapter` facade（4–6）；`EvidenceMigrator` 会话 load/list；`revise_paper` 最多 3 轮 + 安全回退题
- **Edition 0830_9 A2（地区错误 + 会话同步）：** `normalize_region` / 软课标；创建会话 E-004；`GET /sessions/{id}` + heartbeat；前端 `useSessionSync`（可见性拉取、30s 心跳、未保存 beforeunload）
- **Edition 0901（演示单元 + 教学效果）：** `math_5_1` 小数乘法预置闭环会话（C1 seed）；`POST /demo/units/{unit_id}/session`；`TeachingEffectivenessMetrics` + `GET /sessions/{id}/effectiveness` + PDF 导出；Landing「体验完整教学单元」CTA；`EffectivenessDashboard` + 教师/家长 demo 面板；`scripts/generate_demo_effectiveness.py`
- **Edition 0901_1：** 结构化教师/家长摘要 API、Landing 演示角色选择、学生 `session_id` 深链 resume、效果页前后 ComparisonCards、demo seed 写入 `post_assessment_score`
- **Edition 0901_2：** `StudentSummary` builder（seed overlay C）+ `GET /sessions/{id}/summary/student`；demo seed 写入 `metadata.student_summary`；学生计划步 `StudentSummaryPanel`（任务进度 / 星星 / 下一挑战）

---

## 更新日志

| 阶段 | 要点 | 测试 |
| --- | --- | --- |
| Multi-Agent P0 + Composition Phase 1 | 6 Agent 编排、ItemGrader / GradingReceipt、课标 keyword RAG、评测 CLI | 177 |
| Phase 1 收尾 | StepAttempt、contextual 画像、citation ids、completeness CLI 等 | 177 |
| Phase 2a 诊断 / 证据 | OPT-023…026、OPT-074、G-05 | 198 |
| Phase 2b 规划 / 辅导 | OPT-014、OPT-031…034、OPT-060 | 234 |
| Phase 2c 课标 / 多科 | A-03、OPT-041/042、OPT-003、D-04、E-05 → 合入 `master` 并 push | **258** |
| Phase 2d 编排质量 | OPT-050…052、OPT-015、OPT-016 | **283** |
| Edition 0813 P0+P1 | 建档主题、source_refs、四维验证器、情境兴趣、learning_difficulty | **316** |
| Edition 0815 integration | Math-Verify、Guard tiers、CitationPanel、theme tokens；example bank / validators unchanged；0815 drafts remain under `doc/deepseek_edition/0815/` | **349** |
| Edition 0815_e1 assessment UX | 测评步倒计时、MathVisualizer、专注模式 SocraticPanel；`HintInteraction` 每题≤3；草稿见 `doc/deepseek_edition/0815_e1/` | **356** |
| PDF dual export | 做题复盘 + 学习报告 PDF；复用 `report.txt` 数据结构；`/export/assessment.pdf` `/export/report.pdf` | **363** |
| Edition 0825 adaptive cold-start | 进度映射、知识图谱、锚点→完整卷（20 题）、`/assessment/adaptive/*`；默认测评路径不变 | **412** |
| Edition 0825 planning + frontend | 诊断 enrichment、科学规划 markdown/metadata、Tutor 策略前缀、useRole/useResponsive | **416** |
| Edition 0825 dual-layer + Assessment page | 锚点 Layer2（llm/stub）、学生向导接入 `Assessment.tsx` | **418** |
| Edition 0826 curriculum data expansion | `build_pilot` 管线；RCAE/MM-K12/TAL/templates 导入；知识点 13→1294；legacy kp ≥8 例题 | **439** |
| Edition 0827 multimodal curriculum binding | `CurriculumRef`/`CurriculumGate`；MV-MATH→`multimodal_bank`；锚点 2–4 / 完整卷 ≤4 多模态；`/pilot-assets`；Assessment 配图 UI | **459** |
| Edition 0830 cognitive / style / geometry | 认知技能图谱、风格推断与规划适配、JSXGraph 交互几何、processed 导出 | **474** |
| Edition 0830_2 platform hardening A | Settings/日志/缓存/限流/submit 校验 | **487** |
| Edition 0830_3 reliability B | 会话锁/缓存、LLM 降级、诊断规划边界、图谱环检测 | **496** |
| Edition 0830_4 product C | 家长教师摘要、错误归因、干预库、Orchestrator 埋点 | **501** |
| Edition 0830_5 explainability D | 按会话锁、fallback 深度、环依赖硬失败、诊断解释、分层干预 | **507** |
| Edition 0830_6 confidence D | KP 环检测、诊断置信度、提示效果回写、挫败语气 | **514** |
| Edition 0830_7 phase/capabilities D | PhaseGuard、能力注册表、友好错误码 | **522** |
| Edition 0830_8 gap close | 数学 SubjectAdapter、证据迁移、多轮题目修订与安全回退 | **529** |
| Edition 0830_9 A2 地区错误 + 会话同步 | E-004、软课标/地区、GET session + heartbeat、useSessionSync | **535** pytest + **36** vitest |
| Edition 0901 小数乘法演示单元 + 教学效果量化 | math_5_1 seed、demo session API、effectiveness 指标/GET/PDF、Landing CTA、EffectivenessDashboard、角色 demo 面板 | **544** pytest + **52** vitest |
| Edition 0901_1 结构化演示摘要 | 结构化教师/家长摘要 API、Landing 演示角色选择、学生 `session_id` 深链 resume、效果页前后 ComparisonCards、demo seed 写入 `post_assessment_score` | **549** pytest + **62** vitest |
| Edition 0901_2 学生摘要 + 计划步面板 | StudentSummary builder/overlay、GET summary/student、demo seed metadata、计划步 StudentSummaryPanel | **554** pytest + **71** vitest |

---

## 近期 Todo

下一优先包（摘要；完整 ID 见 `doc/composition/TODO.md` §H）：

| 包 | 包含 | 目标 |
| --- | --- | --- |
| **Eval 扩展** | OPT-072/073/081、E-10…E-21 | 公开基准与 Skill registry |
| **文档 / 仓库运维** | F-05…F-07 | hermes / xiaozhi / EduGemma 等研究与索引刷新 |

完成一项后：在本文件「更新日志」追加一行，并视需要上调基线测试数。
