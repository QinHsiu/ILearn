# ILearn

Love learn and I learn.

小学数学学情诊断与学习规划 MVP（四年级至六年级）。

闭环：**练习 → 分步批改 → 学情诊断 → 学习计划 →（薄弱点巩固练习）**。

## 多 Agent 架构（P0）

| Agent | 职责 |
| --- | --- |
| **AssessmentAgent** | 组题：地区/年级课标约束、20 题诊断卷或 1–10 题巩固卷 |
| **PracticeAgent** | 练题批改：客观题规则 + 构造题分步 LLM；支持手写图片 VL 批改 |
| **DiagnosisAgent** | 学情诊断：知识点掌握、能力维度、Top-N 干预；更新学习者画像 |
| **PlanningAgent** | 个性化学习建议：1–2 周计划、课标依据 citation；触发巩固练习环 |
| **CurriculumAgent** | 课标检索与 citation（试点：`data/pilot/` JSON 包） |
| **EvalAgent** | 离线基准：分步批改 fixtures 经 PracticeAgent 跑分 |

编排由 `MultiAgentOrchestrator` 驱动；`ilearn.core.orchestrator.Orchestrator` 为向后兼容门面。

### 阶段状态机

```
ONBOARD → ASSESS → PRACTICE → GRADE → DIAGNOSE → PLAN → PRACTICE_LOOP → …
```

| 阶段 | 触发 Agent | 持久化 |
| --- | --- | --- |
| ONBOARD | — | `StudentProfile` |
| ASSESS | CurriculumAgent + AssessmentAgent | `AssessmentPaper`, `curriculum_citations` |
| PRACTICE | — | `StudentAnswer[]`, `ImageAnswer[]` |
| GRADE | PracticeAgent | `GradeResult[]` |
| DIAGNOSE | DiagnosisAgent | `DiagnosisReport`, `LearnerPortrait` |
| PLAN | PlanningAgent | `LearningPlanReport` |
| PRACTICE_LOOP | AssessmentAgent（薄弱点变式卷） | 新一轮 paper；`loop_count` ≤ 2 |

开源借鉴对照见 [`doc/composition/AGENT_MAPPING.md`](doc/composition/AGENT_MAPPING.md)。

## 安装

Python 3.11+。在仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
# 或：pip install -e ".[dev]"
```

复制环境变量模板并按需填写：

```powershell
copy .env.example .env
```

## 本地运行

### FastAPI（`:8000`）

```powershell
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000
```

API 文档：`http://127.0.0.1:8000/docs`

### Streamlit 教学界面（`:8501`）

另开一个终端，先启动 API，再启动 Streamlit：

```powershell
streamlit run ilearn/web/app.py --server.port 8501
```

浏览器访问 **`http://127.0.0.1:8501`**。界面通过 HTTP 调用 FastAPI（默认 `http://127.0.0.1:8000`），不在 UI 层重复业务逻辑。

若 API 不在本机 8000 端口，启动 Streamlit 前设置：

```powershell
$env:ILEARN_API_BASE = "http://127.0.0.1:8000"
streamlit run ilearn/web/app.py
```

## CLI

### 多 Agent 端到端（推荐）

离线演示（使用 answer key 自动作答，无需 LLM）：

```powershell
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline
```

配置 LLM 时省略 `--offline`，构造题与 VL 批改走在线模型。

### 端到端测评（兼容入口）

```powershell
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer
```

仅生成 20 题试卷（不提交答案）：

```powershell
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11
```

使用外部答案 JSON 提交：

```powershell
python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --answers-file answers.json
```

输出包含 `data/sessions/<id>/paper.json`、`report.md`，以及报告摘要（含 **学情诊断**、**学习者画像** 与 **学习计划**）。

也可通过 Typer 入口：`ilearn run ...` / `ilearn agents run ...` / `ilearn eval`（安装后可执行脚本时）。

### 最小评估（分步批改 fixtures）

```powershell
python -m ilearn.cli.main eval
python -m ilearn.cli.main eval --agents
```

`--agents` 经 EvalAgent → PracticeAgent 跑 benchmark 并打印 `agents_invoked`。

## API 路由

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/sessions` | 建档，返回 `session_id` |
| POST | `/sessions/{id}/assessment` | 组题（20 题诊断卷） |
| POST | `/sessions/{id}/submit` | 提交文本答案 |
| POST | `/sessions/{id}/submit-images` | 提交手写图片（base64） |
| POST | `/sessions/{id}/grade` | 分步批改 |
| POST | `/sessions/{id}/diagnose` | 学情诊断 + 画像更新 |
| POST | `/sessions/{id}/plan` | 生成学习计划 |
| POST | `/sessions/{id}/run` | 提交后一键：批改 → 诊断 → 规划（含巩固环触发） |
| POST | `/sessions/{id}/followup` | 手动启动薄弱点巩固卷 |
| GET | `/sessions/{id}/phase` | 当前阶段与 `loop_count` |
| GET | `/sessions/{id}/report` | Markdown 报告 + 完整 session |

## 环境变量

见 [`.env.example`](.env.example)：

| 变量 | 说明 |
| --- | --- |
| `ILEARN_LLM_BASE_URL` | OpenAI 兼容 API 基址（可选） |
| `ILEARN_LLM_API_KEY` | API Key；设置后 API/CLI 使用 LLM，未设置时客观题走规则、构造题走最终答案提取等离线降级路径 |
| `ILEARN_LLM_MODEL` | 文本模型名（默认 `gpt-4o-mini`） |
| `ILEARN_VISION_MODEL` | 手写/VL 批改专用模型；未设置时回退到 `ILEARN_LLM_MODEL` |
| `ILEARN_API_BASE` | Streamlit 连接的 FastAPI 地址（默认 `http://127.0.0.1:8000`） |

## 测试

```powershell
python -m pytest -q
```

多 Agent E2E（离线，含画像与巩固环）：

```powershell
python -m pytest tests/test_e2e_multi_agent.py -v
```

## MVP 范围

- 小学数学，四至六年级；默认 **20 题**（难度 10/8/2，题型 8/8/4）
- 北京·人教试点课标包（`data/pilot/`）；`region` 非北京时在报告中显式标注课标不匹配
- 分步批改、错误标签、学情 Top-5、学习者画像、1–2 周学习计划（JSON + Markdown）
- 薄弱点 **练→评→练** 正反馈环（最多 2 轮巩固练习，1–10 题/轮）
- FastAPI + Streamlit 向导 + CLI `run` / `agents run` / `eval`
- 手写图片作答与 VL 分步批改（需配置 `ILEARN_VISION_MODEL` 或兼容多模态的 `ILEARN_LLM_MODEL`）
- 会话持久化：`data/sessions/`（JSON，无数据库）
- OpenAI 兼容 LLM（配置后用于构造题/VL 批改；未配置或请求失败时使用规则/离线降级，且结果标记 `grading_degraded`）

## 非目标（本版不做）

- TutorAgent 多轮苏格拉底辅导
- 多科目、实时网页课标爬取
- 教师备课、班级报表、真实学生 PII
- LangGraph / 向量课标 RAG（接口预留，MVP 用试点 JSON）
- 完整 mathtutorbench / EduAgentBench HF 数据集导入（EvalAgent 已接 fixtures hook）

## 项目结构

```
ilearn/
  agents/      # Assessment, Practice, Diagnosis, Planning, Curriculum, Eval
  core/        # 测评、批改、诊断、规划、编排门面
  providers/   # 课标 PilotBeijingRenjiaoProvider、LLMClient（含 VL）
  storage/     # 会话 JSON
  api/         # FastAPI
  cli/         # run / agents run / eval
  web/         # Streamlit
  eval/        # 分步批改 fixtures 评估
data/pilot/    # 试点知识点与题目模板
data/sessions/ # 运行产物
data/eval/     # step_grading / vision_grading fixtures
scripts/       # 试点题库生成脚本（可选）
doc/composition/  # 开源多 Agent 分析与架构文档
```
