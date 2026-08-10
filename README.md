# ILearn

Love learn and I learn.

面向小学数学（四至六年级）的学情诊断与个性化学习规划系统。

闭环：**练习 → 分步批改 → 学情诊断 → 学习计划 →（薄弱点巩固）**。

## 功能概览

| 能力 | 说明 |
| --- | --- |
| 课标约束组卷 | 地区/年级试点课标；诊断卷 20 题（难度 10/8/2，题型 8/8/4）；巩固卷 1–10 题 |
| 分步批改 | 客观题规则 + 构造题 LLM；手写图 OCR 与批改分离；`GradingReceipt` 溯源 |
| 学情诊断 | practice / probe 双轨掌握度、证据日志、五维画像、Top-N 干预 |
| 学习计划 | 1–2 周计划、课标 citation、SM-2 间隔复习日 |
| 巩固环 | 薄弱点练→评→练，最多 2 轮 |
| 离线评测 | 分步批改 fixtures、mistake_location、步骤完整度 |

## 多 Agent 架构

| Agent | 职责 |
| --- | --- |
| **AssessmentAgent** | 组题（PaperBlueprint 两阶段：蓝图 → 填槽 → 校验） |
| **PracticeAgent** | 文本/图片作答批改；OCR → `ItemGrader` |
| **DiagnosisAgent** | 知识点掌握、能力维度、干预建议、画像更新 |
| **PlanningAgent** | 个性化学习计划、课标依据、复习任务 |
| **CurriculumAgent** | 课标检索与 citation（试点 JSON + keyword RAG） |
| **EvalAgent** | 离线基准跑分 |

编排：`MultiAgentOrchestrator`（`ilearn.core.orchestrator.Orchestrator` 为兼容门面）。

### 阶段状态机

```
ONBOARD → ASSESS → PRACTICE → GRADE → DIAGNOSE → PLAN → PRACTICE_LOOP → …
```

| 阶段 | Agent | 持久化 |
| --- | --- | --- |
| ONBOARD | — | `StudentProfile` |
| ASSESS | CurriculumAgent + AssessmentAgent | `AssessmentPaper`, citations |
| PRACTICE | — | `StudentAnswer[]`, `ImageAnswer[]` |
| GRADE | PracticeAgent | `GradeResult[]`, `evidence_log` |
| DIAGNOSE | DiagnosisAgent | `DiagnosisReport`, `LearnerPortrait` |
| PLAN | PlanningAgent | `LearningPlanReport` |
| PRACTICE_LOOP | AssessmentAgent | 巩固卷；`loop_count` ≤ 2 |

## 安装

Python 3.11+。在仓库根目录：

```powershell
python -m pip install -r requirements.txt
# 或：pip install -e ".[dev]"
copy .env.example .env
```

## 本地运行

### FastAPI（`:8000`）

```powershell
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
```

文档：`http://127.0.0.1:8000/docs`

### Streamlit（`:8501`）

先启动 API，再：

```powershell
streamlit run ilearn/web/app.py --server.port 8501
```

默认请求 `http://127.0.0.1:8000`。若 API 地址不同：

```powershell
$env:ILEARN_API_BASE = "http://127.0.0.1:8000"
streamlit run ilearn/web/app.py
```

## CLI

### 多 Agent 端到端（推荐）

```powershell
# 离线演示（answer key 自动作答，无需 LLM）
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline

# 配置 LLM 后省略 --offline
```

### 兼容入口

```powershell
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --answers-file answers.json
```

产物：`data/sessions/<id>/paper.json`、`report.md`。

### 评估

```powershell
python -m ilearn.cli.main eval
python -m ilearn.cli.main eval --agents
python -m ilearn.cli.main eval --mathtutorbench
```

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

## 环境变量

见 [`.env.example`](.env.example)：

| 变量 | 说明 |
| --- | --- |
| `ILEARN_LLM_BASE_URL` | OpenAI 兼容 API 基址（可选） |
| `ILEARN_LLM_API_KEY` | 有则走 LLM；无则客观题规则 + 构造题离线降级 |
| `ILEARN_LLM_MODEL` | 文本模型（默认 `gpt-4o-mini`） |
| `ILEARN_VISION_MODEL` | VL/手写模型；未设则回退文本模型 |
| `ILEARN_API_BASE` | Streamlit 连接的 API（默认 `http://127.0.0.1:8000`） |

## 测试

```powershell
python -m pytest -q
python -m pytest tests/test_e2e_multi_agent.py tests/test_e2e_composition_phase1.py -v
```

## 本版范围

- 小学数学四至六年级；默认诊断卷 20 题
- 试点课标：**北京·人教**（`data/pilot/`）；非北京 region 在报告中标注课标不匹配
- 分步批改、错误标签、学情 Top-5、学习者画像、1–2 周计划
- 巩固环最多 2 轮；会话 JSON 持久化（`data/sessions/`）
- FastAPI + Streamlit + CLI；OpenAI 兼容 LLM（可选，失败时 `grading_degraded`）

## 非目标（本版不做）

- TutorAgent 多轮苏格拉底辅导
- 多科目、实时网页课标爬取
- 教师备课、班级报表、真实学生 PII
- LangGraph / 向量课标库（当前为试点 JSON + keyword RAG）

## 项目结构

```
ilearn/
  agents/      # Assessment, Practice, Diagnosis, Planning, Curriculum, Eval
  core/        # 测评、批改、证据、诊断、规划、OCR、复习
  providers/   # 课标、keyword RAG、LLM（含 VL）
  storage/     # 会话 JSON
  api/         # FastAPI
  cli/         # run / agents run / eval
  web/         # Streamlit
  eval/        # 离线基准
data/pilot/    # 试点知识点与模板
data/sessions/ # 运行产物
data/eval/     # 评测 fixtures
```

## 致谢

感谢教育 AI 开源社区的贡献。致谢名单见 [REFERENCE.md](REFERENCE.md)。
