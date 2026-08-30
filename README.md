# ILearn

**课标在环 · 多 Agent 协同 · 自适应个性化学习引擎**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](./frontend)
[![Tests](https://img.shields.io/badge/tests-496%20passed-2ea44f)](./tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/GitHub-QinHsiu%2FILearn-181717?logo=github)](https://github.com/QinHsiu/ILearn)

让每个孩子拥有课标对齐、数据驱动、持续进化的 AI 学习伙伴。

```text
测评 → 批改 → 诊断 → 规划 → 巩固
  │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼
Curriculum · Assessment · Practice · Diagnosis · Planning
                    └────── Tutor ──────┘
                       苏格拉底引导
```

当前试点：小学数学（四至六年级）· 北京·人教。架构按多学科 / 全学段扩展预留。

## 特性

- **课标在环** — 建议可追溯到课标条目与例题来源
- **批改可审计** — OCR 与判分分离，`GradingReceipt` 可复现
- **掌握度严谨** — practice / probe 双轨 + 证据日志
- **辅导不泄题** — 状态机驱动的苏格拉底提示（Guard 护栏）
- **报告可带走** — 一键导出做题复盘 PDF 与学习报告 PDF
- **多形态交付** — CLI · REST API · React 向导
- **零 LLM 可跑** — 无 API Key 亦可离线演示全流程
- **496+ 测试** — 离线基准保障工程质量

## 60 秒上手

Python **3.11+**，在仓库根目录：

```bash
python -m pip install -e ".[dev]"
cp .env.example .env   # Windows: copy .env.example .env

# 离线跑通闭环（无需 API Key）
python -m ilearn.cli.main agents run --region 北京 --grade 5 --age 11 --offline
```

教学向导（两个终端）：

```bash
# 终端 1 — API
uvicorn ilearn.api.app:app --reload --host 127.0.0.1 --port 8000

# 终端 2 — React
cd frontend && npm install && npm run dev
```

| 入口 | 地址 |
| --- | --- |
| Web 向导 | http://127.0.0.1:5173 |
| API 文档 | http://127.0.0.1:8000/docs |

## 文档

| 文档 | 内容 |
| --- | --- |
| **[INTRODUCTION.md](INTRODUCTION.md)** | 架构、能力、API / CLI、环境变量、目录说明 |
| **[VERSION.md](VERSION.md)** | 版本范围、更新日志、近期 Todo |
| **[REFERENCE.md](REFERENCE.md)** | 致谢与参考项目 |
| OpenAPI | 启动 API 后见 `/docs` |

## 贡献

```bash
pip install -e ".[dev]"
python -m pytest -q
cd frontend && npm test && npm run build
```

欢迎 Issue 与 Pull Request。

## License

MIT © ILearn Contributors

<p align="center"><b>ILearn</b> — Love learn · I learn.</p>
