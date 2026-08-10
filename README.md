# ILearn

**Love learn · I learn.**

> 面向 **K12 全学段** 的学情诊断与个性化学习规划多 Agent 系统。  
> 一次测评 → 分步批改 → 精准诊断 → 课标对齐的学习计划 → 薄弱点巩固闭环。  
> **当前试点：** 小学数学（四至六年级）· 北京·人教课标包；架构按多学科 / 全学段扩展预留。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-177%20passed-2ea44f)](./tests)
[![GitHub](https://img.shields.io/badge/GitHub-QinHsiu%2FILearn-181717?logo=github)](https://github.com/QinHsiu/ILearn)

```text
  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────┐
  │  组卷   │ → │ 练习作答│ → │ 分步批改│ → │ 学情诊断│ → │ 个性化学习计划│
  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └──────┬───────┘
       ▲                                                         │
       └─────────────── 薄弱点巩固（最多 2 轮） ◄────────────────┘
```

---

## 为什么是 ILearn

| | |
| --- | --- |
| **课标在环** | 地区 / 年级课标约束 + keyword RAG citation；当前试点「北京·人教」，计划可追溯到纲要依据 |
| **批改可审计** | Host-owned `ItemGrader`；OCR 与判分分离；`GradingReceipt` 绑定试卷与 grader 版本 |
| **掌握度不糊弄** | practice / probe 双轨 + `KnowledgeEvidence` 证据日志，避免「带提示做对」当成已掌握 |
| **多 Agent 编排** | 六大 Agent + 明确状态机，而不是一个巨型 prompt |
| **开箱可跑** | 无 LLM 也能离线演示全流程；配置 OpenAI 兼容 API 即升级构造题 / 手写 VL |

---

## 核心能力

| 能力 | 你得到什么 |
| --- | --- |
| **课标约束组卷** | 诊断卷 20 题（难度 10/8/2，题型 8/8/4）；PaperBlueprint 两阶段组卷；巩固卷 1–10 题 |
| **分步批改** | 客观题规则 + 构造题 LLM；手写图 OCR → 文本批改；错误标签受控、结果可降级标记 |
| **学情诊断** | 知识点掌握、五维画像、Top-N 干预建议、SM-2 间隔复习状态 |
| **学习计划** | 1–2 周 Markdown / JSON 计划，含课标 citation 与复习日 |
| **巩固闭环** | 诊断后按薄弱点自动触发练→评→练（`loop_count` ≤ 2） |
| **离线评测** | 分步 fixtures、mistake_location、步骤完整度基准 |

---

## 多 Agent 架构

六个专职 Agent，由 `MultiAgentOrchestrator` 驱动（`ilearn.core.orchestrator.Orchestrator` 为兼容门面）。

| Agent | 一句话职责 |
| --- | --- |
| **AssessmentAgent** | 蓝图 → 填槽 → 校验，产出诊断卷 / 巩固卷 |
| **PracticeAgent** | 文本与图片作答批改；OCR → `ItemGrader` |
| **DiagnosisAgent** | 掌握度、证据、画像、干预建议 |
| **PlanningAgent** | 个性化计划、课标依据、复习任务 |
| **CurriculumAgent** | 课标检索与 citation |
| **EvalAgent** | 离线基准跑分 |

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
| PRACTICE_LOOP | Assessment | 巩固卷；`loop_count` ≤ 2 |

---

## 60 秒上手

Python **3.11+**。在仓库根目录：

```powershell
python -m pip install -r requirements.txt
copy .env.example .env

# 离线跑通整条多 Agent 闭环（无需 API Key）
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline
```

会话产物在 `data/sessions/<id>/`（`paper.json`、`report.md` 等）。

想看教学向导界面：先起 API，再起 Streamlit。

```powershell
# 终端 1
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000

# 终端 2
streamlit run ilearn/web/app.py --server.port 8501
```

| 入口 | 地址 |
| --- | --- |
| API 文档 | http://127.0.0.1:8000/docs |
| Streamlit | http://127.0.0.1:8501 |

配置 LLM 后，去掉 `--offline`，构造题与 VL 手写批改走在线模型（见下方环境变量）。

---

## CLI

```powershell
# 多 Agent 端到端（推荐）
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline

# 兼容入口：自动作答 / 仅组卷 / 外部答案文件
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --answers-file answers.json

# 评估
python -m ilearn.cli.main eval
python -m ilearn.cli.main eval --agents
python -m ilearn.cli.main eval --mathtutorbench
python -m ilearn.cli.main eval --completeness      # TutorGym 步骤完整度
python -m ilearn.cli.main eval --mistake-correction  # MathTutorBench 错因纠正
python -m ilearn.cli.main eval --scaffolding         # MathTutorBench 脚手架 hint 级别
```

也可安装后使用：`ilearn agents run …` / `ilearn eval …`。

---

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/sessions` | 建档 |
| POST | `/sessions/{id}/assessment` | 组题 |
| POST | `/sessions/{id}/submit` | 提交文本答案 |
| POST | `/sessions/{id}/submit-images` | 提交手写图片（base64） |
| POST | `/sessions/{id}/grade` | 批改 |
| POST | `/sessions/{id}/diagnose` | 诊断 + 画像 |
| POST | `/sessions/{id}/plan` | 学习计划 |
| POST | `/sessions/{id}/run` | 批改 → 诊断 → 规划（含巩固环） |
| POST | `/sessions/{id}/followup` | 手动启动巩固卷 |
| GET | `/sessions/{id}/phase` | 当前阶段 |
| GET | `/sessions/{id}/report` | Markdown 报告 |

Streamlit 若连非本机 API：

```powershell
$env:ILEARN_API_BASE = "http://127.0.0.1:8000"
streamlit run ilearn/web/app.py
```

---

## 环境变量

见 [`.env.example`](.env.example)。

| 变量 | 说明 |
| --- | --- |
| `ILEARN_LLM_BASE_URL` | OpenAI 兼容 API 基址（可选） |
| `ILEARN_LLM_API_KEY` | 有则走 LLM；无则规则 + 离线降级 |
| `ILEARN_LLM_MODEL` | 文本模型（默认 `gpt-4o-mini`） |
| `ILEARN_VISION_MODEL` | VL / 手写模型；未设则回退文本模型 |
| `ILEARN_API_BASE` | Streamlit 连接的 API（默认 `http://127.0.0.1:8000`） |

---

## 测试

```powershell
python -m pytest -q
python -m pytest tests/test_e2e_multi_agent.py tests/test_e2e_composition_phase1.py -v
```

当前仓库基线：**177** 项测试通过（离线可跑）。

---

## 定位、本版范围与非目标

**产品定位：** K12 全学段学情诊断与个性化学习规划（多科目可扩展）。

**本版已落地（试点）**

- 首发试点学科 / 学段：**小学数学（四至六年级）**；默认诊断卷 20 题
- 试点课标：**北京·人教**（`data/pilot/`）；非北京 region 在报告中标注课标不匹配
- 分步批改、错误标签、学情 Top-5、学习者画像、1–2 周计划、巩固环（≤ 2）
- FastAPI + Streamlit + CLI；会话 JSON 持久化；OpenAI 兼容 LLM（可选）

**本版不做**

- TutorAgent 多轮苏格拉底辅导
- 多科目并行上线、实时网页课标爬取
- 教师备课、班级报表、真实学生 PII
- LangGraph / 向量课标库（当前为试点 JSON + keyword RAG）

---

## 项目结构

```text
ilearn/
  agents/      # Assessment · Practice · Diagnosis · Planning · Curriculum · Eval
  core/        # 测评 · 批改 · 证据 · 诊断 · 规划 · OCR · 复习
  providers/   # 课标 · keyword RAG · LLM（含 VL）
  storage/     # 会话 JSON
  api/         # FastAPI
  cli/         # run / agents run / eval
  web/         # Streamlit
  eval/        # 离线基准
data/pilot/    # 试点知识点与模板
data/sessions/ # 运行产物
data/eval/     # 评测 fixtures
```

---

## 致谢

站在教育 AI 开源社区的肩膀上。致谢名单见 **[REFERENCE.md](REFERENCE.md)**。

---

<p align="center">
  <b>ILearn</b> — Love learn · I learn.
</p>
