# ILearn

小学数学学情诊断与学习规划 MVP（四年级至六年级）。

闭环：**练习 → 分步批改 → 学情诊断 → 学习计划**。

## 安装

Python 3.11+。在项目根目录（`projects/ILearn`）执行：

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

### 端到端测评

使用试卷 `answer_key` 自动作答；配置 LLM 时会用于构造题分步批改，未配置时自动使用规则/离线降级批改：

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

输出包含 `data/sessions/<id>/paper.json`、`report.md`，以及报告摘要（含 **学情诊断** 与 **学习计划**）。

也可通过 Typer 入口：`ilearn run ...` / `ilearn eval`（安装后可执行脚本时）。

### 最小评估（分步批改 fixtures）

```powershell
python -m ilearn.cli.main eval
```

打印 `accuracy`、`macro_f1`、`json_valid_rate`（默认离线规则批改；加 `--use-llm` 才用已配置的 LLM）。

## 环境变量

见 [`.env.example`](.env.example)：

| 变量 | 说明 |
| --- | --- |
| `ILEARN_LLM_BASE_URL` | OpenAI 兼容 API 基址（可选） |
| `ILEARN_LLM_API_KEY` | API Key；设置后 API/CLI 使用 LLM，未设置时客观题走规则、构造题走最终答案提取等离线降级路径 |
| `ILEARN_LLM_MODEL` | 模型名（默认 `gpt-4o-mini`） |
| `ILEARN_API_BASE` | Streamlit 连接的 FastAPI 地址（默认 `http://127.0.0.1:8000`） |

## 测试

```powershell
python -m pytest -q
```

## MVP 范围

- 小学数学，四至六年级；默认 **20 题**（难度 10/8/2，题型 8/8/4）
- 北京·人教试点课标包（`data/pilot/`）；`region` 非北京时在报告中显式标注课标不匹配
- 分步批改、错误标签、学情 Top-5、1–2 周学习计划（JSON + Markdown）
- FastAPI + Streamlit 四步向导 + CLI `run` / `eval`
- 会话持久化：`data/sessions/`（JSON，无数据库）
- OpenAI 兼容 LLM（配置后用于构造题批改；未配置或请求失败时使用规则/离线降级，且结果标记 `grading_degraded`）

## 非目标（本版不做）

- 视觉 / 拍照作答（VL）
- 多科目、实时网页课标爬取
- 多轮苏格拉底式辅导、每次练习后自动重规划
- 教师备课、班级报表、真实学生 PII
- LangGraph / RAG 课标检索（接口预留，MVP 未实现）

## 项目结构

```
ilearn/
  core/        # 测评、批改、诊断、规划、编排
  providers/   # 课标 PilotBeijingRenjiaoProvider、LLMClient
  storage/     # 会话 JSON
  api/         # FastAPI
  cli/         # run / eval
  web/         # Streamlit
  eval/        # 分步批改 fixtures 评估
data/pilot/    # 试点知识点与题目模板
data/sessions/ # 运行产物
```

设计说明见 `docs/superpowers/specs/2026-08-10-ilearn-mvp-design.md`。
