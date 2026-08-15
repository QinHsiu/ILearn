# ILearn 介绍

本页承接根目录 [README.md](README.md) 的展开说明：架构、能力、API / CLI、配置与目录。  
上手步骤与一句话使命见 README。

---

## 为什么是 ILearn

| | |
| --- | --- |
| **课标在环** | 地区 / 年级课标约束 + 可切换 retriever（`keyword` / `hash_vector`）；多地区 source packs；计划可追溯到纲要依据 |
| **批改可审计** | Host-owned `ItemGrader`；OCR 与判分分离；`GradingReceipt` 绑定试卷与 grader 版本 |
| **掌握度不糊弄** | practice / probe 双轨 + `KnowledgeEvidence`，避免「带提示做对」当成已掌握 |
| **多 Agent 编排** | 流水线 Agent + Tutor + Eval，由状态机编排，而不是一个巨型 prompt |
| **编排可观测** | 上下文预算、`decision_log`、阶段质量门、PendingQuestion 绑题、写能力白名单 |
| **开箱可跑** | 无 LLM 也能离线演示；配置 OpenAI 兼容 API 即升级构造题 / 手写 VL |
| **建档与主题** | 昵称 / 性别；React 向导按性别 × 学段切换主题 |
| **题目溯源** | 组卷绑定 `source_refs`；报告与向导可展开错题参考来源 |
| **题目质量门** | 四维验证器（可解 / 现实 / 可读 / 情境）+ 单次修订 |
| **双轨个性化** | `situation_interest`；巩固组卷优先匹配偏好情境；`learning_difficulty` 可扩巩固环 |
| **报告导出** | 学习计划页一键导出做题复盘 PDF / 学习报告 PDF（后端生成） |

---

## 核心能力

| 能力 | 你得到什么 |
| --- | --- |
| **课标约束组卷** | 诊断卷 20 题（难度 10/8/2，题型 8/8/4）；巩固卷 1–10 题 |
| **分步批改** | 客观题规则 + 构造题 LLM；手写 OCR → 文本批改；Hint Ladder（不泄答案） |
| **学情诊断** | 知识点掌握、能力估算、Top-N 干预、证据与 leech / probe gap |
| **学习计划** | 1–2 周计划，含课标 citation、挫败 replan、版本历史 |
| **苏格拉底辅导** | Tutor 状态机 + Guard；HTTP：`/tutor`、`/tutor/hint` |
| **巩固闭环** | 薄弱点练→评→练（默认 `loop_count` ≤ 2） |
| **离线评测** | fixtures、mistake_location、步骤完整度等 CLI 基准 |
| **PDF 导出** | `GET .../export/assessment.pdf`、`.../export/report.pdf` |

---

## 多 Agent 架构

由 `MultiAgentOrchestrator` 驱动（`ilearn.core.orchestrator.Orchestrator` 为兼容门面）：

| Agent | 角色 | 职责 |
| --- | --- | --- |
| **CurriculumAgent** | 流水线 | 课标检索与 citation |
| **AssessmentAgent** | 流水线 | 蓝图 → 填槽 → 校验，产出诊断卷 / 巩固卷 |
| **PracticeAgent** | 流水线 | 文本与图片作答批改 |
| **DiagnosisAgent** | 流水线 | 掌握度、证据、画像、干预 |
| **PlanningAgent** | 流水线 | 个性化计划与 replan |
| **TutorAgent** | 辅导 | 苏格拉底提示；Guard 防泄题 |
| **EvalAgent** | 离线评测 | CLI `ilearn eval`，不进会话流水线 |

### 会话阶段

```text
ONBOARD → ASSESS → PRACTICE → GRADE → DIAGNOSE → PLAN → PRACTICE_LOOP → …
```

| 阶段 | 谁在干活 | 落盘什么 |
| --- | --- | --- |
| ONBOARD | — | `StudentProfile` |
| ASSESS | Curriculum + Assessment | `AssessmentPaper`, citations |
| PRACTICE | 学习者 | `StudentAnswer[]` / `ImageAnswer[]` |
| GRADE | Practice | `GradeResult[]`, `evidence_log` |
| DIAGNOSE | Diagnosis | `DiagnosisReport`, `LearnerPortrait` |
| PLAN | Planning | `LearningPlanReport` |
| PRACTICE_LOOP | Assessment | 巩固卷；`loop_count` 受限 |

---

## CLI

```bash
# 多 Agent 端到端（推荐）
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline

# 兼容入口
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --answers-file answers.json

# 评估
python -m ilearn.cli.main eval
python -m ilearn.cli.main eval --agents
python -m ilearn.cli.main eval --mathtutorbench
python -m ilearn.cli.main eval --completeness
python -m ilearn.cli.main eval --mistake-correction
python -m ilearn.cli.main eval --scaffolding
```

安装后也可：`ilearn agents run …` / `ilearn eval …`。

会话产物默认在 `data/sessions/`。

---

## API

启动 API 后，完整契约见 **http://127.0.0.1:8000/docs**。与 `ilearn/api/app.py` 一致的主干路由：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/sessions` | 建档 |
| GET | `/sessions?nickname=` | 按昵称查看历史 |
| DELETE | `/sessions/{session_id}` | 删除历史 |
| POST | `/sessions/{session_id}/assessment` | 组题 |
| POST | `/sessions/{session_id}/submit` | 提交文本答案 |
| POST | `/sessions/{session_id}/submit-images` | 提交手写图片 |
| POST | `/sessions/{session_id}/grade` | 批改 |
| POST | `/sessions/{session_id}/diagnose` | 诊断 |
| POST | `/sessions/{session_id}/plan` | 学习计划 |
| POST | `/sessions/{session_id}/run` | 批改 → 诊断 → 规划（含巩固环） |
| POST | `/sessions/{session_id}/followup` | 手动启动巩固卷 |
| POST | `/sessions/{session_id}/tutor` | 启动苏格拉底辅导 |
| POST | `/sessions/{session_id}/tutor/hint` | 下一条提示 |
| POST | `/sessions/{session_id}/replan` | 重新规划 |
| GET | `/sessions/{session_id}/phase` | 当前阶段 |
| GET | `/sessions/{session_id}/report` | Markdown 报告 |
| GET | `/sessions/{session_id}/export/assessment.pdf` | 做题复盘 PDF |
| GET | `/sessions/{session_id}/export/report.pdf` | 学习报告 PDF |

生产构建：在 `frontend/` 执行 `npm run build` 后，FastAPI 可托管 `frontend/dist`。

> Streamlit（`ilearn/web/app.py`）仅作遗留对照，主 UI 为 React 向导。

---

## 环境变量

见 [`.env.example`](.env.example)。

| 变量 | 说明 |
| --- | --- |
| `ILEARN_LLM_BASE_URL` | OpenAI 兼容 API 基址（可选） |
| `ILEARN_LLM_API_KEY` | 有则走 LLM；无则规则 + 离线降级 |
| `ILEARN_LLM_MODEL` | 文本模型（默认 `gpt-4o-mini`） |
| `ILEARN_VISION_MODEL` | VL / 手写模型；未设则回退文本模型 |
| `ILEARN_API_BASE` | 遗留 Streamlit 连接的 API |
| `ILEARN_RETRIEVER_BACKEND` | `keyword`（默认）/ `hash_vector`；`qdrant` 为 stub |
| `ILEARN_API_TARGET` | 前端 Vite 开发代理目标（默认 `http://127.0.0.1:8000`） |

---

## 测试

```bash
python -m pytest -q
cd frontend && npm test && npm run build
```

当前基线见 [VERSION.md](VERSION.md)（离线可跑；以 `pytest -q` 为准）。

---

## 项目结构

```text
ilearn/
  agents/      # Assessment · Practice · Diagnosis · Planning · Curriculum · Tutor · Eval
  core/        # 测评 · 批改 · 证据 · 诊断 · 规划 · 导出 PDF · OCR · 复习
  providers/   # 课标 · RAG · LLM
  storage/     # 会话 JSON
  api/         # FastAPI（可托管 frontend/dist）
  cli/         # run / agents run / eval
  web/         # Streamlit（已弃用主入口）
  eval/        # 离线基准
frontend/      # React + Vite 教学向导（主 Web UI）
data/pilot/    # 试点知识点与模板；regions/ 多地区 packs
data/sessions/ # 运行产物
data/eval/     # 评测 fixtures
tests/         # 离线测试
```

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11+ · FastAPI · Pydantic |
| 前端 | React · TypeScript · Vite |
| Agent | `MultiAgentOrchestrator` 流水线 |
| 模型 | OpenAI 兼容 API（可替换） |
| PDF | WeasyPrint（优先）/ fpdf2（回退） |
| 测试 | Pytest · Vitest · 离线 fixtures |

---

## 相关文档

- [README.md](README.md) — 使命、特性、60 秒上手
- [VERSION.md](VERSION.md) — 版本与 Todo
- [REFERENCE.md](REFERENCE.md) — 致谢
