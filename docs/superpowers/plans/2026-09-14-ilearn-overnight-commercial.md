# ILearn Overnight Commercial Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在一晚内完成 ILearn **软上线 + 路演获客包**（公网可演示、候补留资、核心闭环可信、竞品叙事清晰），且不偏离「课标在环 · 不泄题 · 证据化掌握度」初衷。

**Architecture:** 在现有 FastAPI + React 向导上做**旁路商业化增量**：Landing 转化、Waitlist API、家长行动摘要、教师分层 CTA、生产粘合与冒烟；不重写 MultiAgent 主链路；Enhanced Flag 保持默认关闭。

**Tech Stack:** Python 3.11 · FastAPI · React/Vite/TS · Pytest/Vitest · 现有 SessionStore / demo unit API

## Global Constraints

- 初衷锚点：课标在环、批改可审计、掌握度双轨、Tutor 不泄终答、试点诚实（小学数学 4–6 · 北京·人教）
- 不做：正式支付、多租户、全科扩展、Enhanced 默认开启
- 对外文案禁止：「秒出答案」「代写作业」「全科已商用」
- 时间盒：每轮迭代 **35–45 分钟**；超时砍 scope 保 DoD
- 规格来源：`docs/superpowers/specs/2026-09-14-ilearn-commercial-launch-design.md`

### File map（预计触达）

| 文件 | 职责 |
| --- | --- |
| `frontend/src/pages/LandingPage.tsx` | 商业价值主张、CTA、候补表单入口 |
| `frontend/src/pages/LegalPrivacy.tsx`（新建） | 隐私与能力边界 |
| `frontend/src/pages/CommercialDiff.tsx` 或 Landing 内嵌 | 竞品差异一句话 |
| `ilearn/api/app.py` | 注册 waitlist / health / 静态 |
| `ilearn/api/waitlist.py`（新建） | 候补写入 |
| `ilearn/core/parent_action_summary.py`（新建或扩展现有 summary） | 家长一分钟行动摘要 |
| `docs/commercial/COMPETITORS.md` | 竞品一页纸 |
| `runtime_evidence/launch_smoke.md` | 冒烟记录 |
| `VERSION.md` | 追加 Edition 0914 commercial 行 |

---

## Iteration 0 — 范围冻结与初衷门禁（T+0 ~ 15min）

**Files:**
- Create: `docs/commercial/LAUNCH_SCOPE.md`
- Modify: none required beyond doc

**Interfaces:**
- Produces: 书面 DoD 与非目标列表（供后续轮次引用）

- [ ] **Step 1:** 将规格 §1 成功标准复制为 `LAUNCH_SCOPE.md`（含 Non-goals）
- [ ] **Step 2:** 确认分支可工作：`pytest tests/test_summary_api.py -q` 与前端 `npm test -- --run LandingPage` 基线可跑
- [ ] **Step 3:** Commit `docs: freeze overnight commercial launch scope`

**验收:** 任何人打开 `LAUNCH_SCOPE.md` 能判断某功能是否该做。

---

## Iteration 1 — 竞品一页纸与对外叙事（T+15 ~ 50min）

**Files:**
- Create: `docs/commercial/COMPETITORS.md`
- Modify: `frontend/src/pages/LandingPage.tsx`（叙事文案区块）

**Interfaces:**
- Consumes: 规格 §2 十二竞品表
- Produces: Landing 主标题/副标题/差异三点

- [ ] **Step 1:** 写 `COMPETITORS.md`（12 竞品 + ILearn 差异化一句话）
- [ ] **Step 2:** Landing 文案改为：

```text
主标题：课标在环的 AI 学习伙伴
副标题：测评 → 批改 → 诊断 → 规划 → 巩固；辅导不泄题，掌握度有证据
三点：课标可追溯 · 苏格拉底护栏 · 报告可带走
```

- [ ] **Step 3:** 更新/补充 `LandingPage.test.tsx` 断言主标题关键词「课标」
- [ ] **Step 4:** `cd frontend && npm test -- --run LandingPage`
- [ ] **Step 5:** Commit `feat(commercial): competitor one-pager and landing promise copy`

**验收:** 去掉导航后首页仍能识别为 ILearn 课标叙事（非搜题器）。

---

## Iteration 2 — Waitlist API + 落盘（T+50 ~ 1h25）

**Files:**
- Create: `ilearn/api/waitlist.py`
- Create: `tests/test_waitlist_api.py`
- Modify: `ilearn/api/app.py`

**Interfaces:**
- Produces: `POST /waitlist` body `{email: str, role: "parent"|"teacher"|"other", note?: str}` → `{ok: true}`
- Side effect: append JSON line to `data/waitlist.jsonl`

- [ ] **Step 1:** 写失败测试：`POST /waitlist` 缺邮箱 → 422

```python
def test_waitlist_requires_email(client):
    r = client.post("/waitlist", json={"role": "parent"})
    assert r.status_code == 422
```

- [ ] **Step 2:** 实现 Pydantic 模型 + 写文件（目录自动创建；简单邮箱正则）
- [ ] **Step 3:** 成功用例：写入后文件末行含 email
- [ ] **Step 4:** 将 `data/waitlist.jsonl` 加入 `.gitignore`（若未忽略）
- [ ] **Step 5:** Commit `feat(api): waitlist capture for commercial soft launch`

**验收:** curl 能写入候补；无密钥泄漏。

---

## Iteration 3 — Landing 候补表单 UX（T+1h25 ~ 2h）

**Files:**
- Modify: `frontend/src/pages/LandingPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/LandingPage.test.tsx`

**Interfaces:**
- Consumes: `POST /waitlist`
- Produces: 表单成功态「已加入早鸟候补」

- [ ] **Step 1:** `client.submitWaitlist({email, role})`
- [ ] **Step 2:** Landing 增加邮箱 + 角色选择 + 提交；与 Demo CTA 并排但不抢演示主 CTA
- [ ] **Step 3:** Vitest：mock fetch 成功后出现成功文案
- [ ] **Step 4:** Commit `feat(frontend): waitlist form on landing`

**验收:** 无后端时有可读错误；有后端时成功提示。

---

## Iteration 4 — 生产健康检查与静态托管确认（T+2h ~ 2h40）

**Files:**
- Modify: `ilearn/api/app.py`（若无 `/healthz`）
- Create: `tests/test_healthz.py`
- Modify: `README.md` 增加「生产启动」三行

**Interfaces:**
- Produces: `GET /healthz` → `{status:"ok", service:"ilearn"}`

- [ ] **Step 1:** 测试 healthz
- [ ] **Step 2:** 实现（幂等，若已存在则补字段）
- [ ] **Step 3:** 文档：`uvicorn ilearn.api.app:app --host 0.0.0.0 --port 8000` + 先 `npm run build`
- [ ] **Step 4:** Commit `feat(api): healthz for launch probes`

**验收:** 公网探活可用。

---

## Iteration 5 — 学生闭环可信：计时公平冒烟（T+2h40 ~ 3h25）

**Files:**
- Verify: `frontend/src/hooks/useCountdown.ts`, `frontend/src/lib/timerEvents.ts`, `Assessment.tsx`
- Create: `runtime_evidence/timer_fairness_smoke.md`

**Interfaces:**
- Consumes: 已有 timer pause/resume + telemetry（当前分支）

- [ ] **Step 1:** 跑相关 vitest：`npm test -- --run useCountdown` 与 timer 相关测试
- [ ] **Step 2:** 手动清单写入 smoke：提交反馈期间倒计时应暂停
- [ ] **Step 3:** 若失败：最小修复 pause 边界（不重做设计）
- [ ] **Step 4:** Commit 仅当有代码修复；否则只提交 evidence

**验收:** 「系统动画吃掉作答时间」问题在演示路径上不可复现。

---

## Iteration 6 — Demo 单元一键路径硬化（T+3h25 ~ 4h10）

**Files:**
- Modify: `frontend/src/pages/LandingPage.tsx`（错误态更清晰）
- Verify: `POST /demo/units/math_5_1/session` 及相关 seed
- Create: `scripts/smoke_demo_unit.py`（可选）

**Interfaces:**
- Consumes: 现有 demo session API
- Produces: 三角色进入后 60s 内可见关键面板

- [ ] **Step 1:** API 冒烟创建 demo session，断言有 diagnosis/plan 元数据或 seed 字段
- [ ] **Step 2:** Landing 失败时展示可复制错误（非空白）
- [ ] **Step 3:** Commit `fix(demo): harden one-click demo error surfacing`

**验收:** 学生/家长/教师三条演示路径可讲完「初衷故事」。

---

## Iteration 7 — 家长一分钟行动摘要（T+4h10 ~ 5h）

**Files:**
- Create or extend: `ilearn/core/parent_action_summary.py`
- Modify: parent summary API 或 dashboard 响应
- Modify: 家长前端面板组件
- Create: `tests/test_parent_action_summary.py`

**Interfaces:**
- Produces: `{headline: str, wins: str[], focus: str[], actions: str[]}` 最多各 2/2/3 条，口语化，无裸术语 ID

- [ ] **Step 1:** 单测：弱项 KP → actions 含「每天 5 分钟」类可执行句
- [ ] **Step 2:** 最小实现（规则模板，不依赖 LLM）
- [ ] **Step 3:** 挂到现有家长摘要 API 字段 `action_summary`
- [ ] **Step 4:** UI 置顶展示
- [ ] **Step 5:** Commit `feat: parent one-minute action summary`

**验收:** 家长 10 秒内知道今晚回家做什么。

---

## Iteration 8 — 教师「下一步」分层建议（最小）（T+5h ~ 5h45）

**Files:**
- Extend teacher demo panel 或 dashboard
- Create: `ilearn/core/tier_suggest.py`
- Create: `tests/test_tier_suggest.py`

**Interfaces:**
- Produces: `{basic: [], advanced: [], challenge: [], next_step: str}`
- 规则：平均掌握度 <0.4 basic；<0.7 advanced；else challenge（与规格 edition 建议一致）

- [ ] **Step 1:** 单测三档分类
- [ ] **Step 2:** Demo 教师视图展示分层人数 + 一句 next_step（「基础组先练小数意义」类模板）
- [ ] **Step 3:** Commit `feat: teacher tier suggestion for demo decisions`

**验收:** 教师端不是纯展示，至少有一个可说的「下一步」。

---

## Iteration 9 — 隐私 / 能力边界页（T+5h45 ~ 6h20）

**Files:**
- Create: `frontend/src/pages/LegalPrivacy.tsx`
- Modify: `App.tsx` 路由
- Modify: Landing footer 链接

**Interfaces:**
- Route: `/privacy`
- Content MUST state: 演示数据、试点学段、不收集身份证、辅导不直接给终答、LLM 可选

- [ ] **Step 1:** 静态页面（中文）
- [ ] **Step 2:** 链接接入 Landing
- [ ] **Step 3:** 简单 render 测试
- [ ] **Step 4:** Commit `feat: privacy and capability boundary page`

**验收:** 公开展示合规姿态，支撑软上线。

---

## Iteration 10 — Tutor 柔性出口（不泄题）（T+6h20 ~ 7h）

**Files:**
- Modify: `ilearn/agents/tutor.py`（或 hint 路径）
- Create/Modify: tests for hint exhausted soft exit

**Interfaces:**
- When hint count ≥ max: return `action: "suggest_review"` + 鼓励性文案 + **不包含最终数值答案**
- 保持 Guard

- [ ] **Step 1:** 测试：exhausted hint 响应无终答数字模式（对已知 fixture）
- [ ] **Step 2:** 实现柔性出口文案（微课/回顾概念/请教老师）
- [ ] **Step 3:** Commit `feat(tutor): soft exit without revealing final answer`

**验收:** 对齐 Khanmigo 伦理；区别于搜题竞品。

---

## Iteration 11 — 路演资产打包（T+7h ~ 7h40）

**Files:**
- Create: `docs/commercial/PITCH_ONEPAGER.md`
- Create: `docs/commercial/DEMO_SCRIPT_5MIN.md`
- Update: `VERSION.md` 追加 Edition 0914 commercial

**Interfaces:**
- Produces: 5 分钟口播脚本（学生 2min / 家长 1.5 / 教师 1.5）

- [ ] **Step 1:** 一页纸：问题 → 方案 → 初衷 → 竞品差异 → 今晚 Demo URL → 候补
- [ ] **Step 2:** 5 分钟脚本对齐 `math_5_1` 演示单元
- [ ] **Step 3:** VERSION 更新日志一行
- [ ] **Step 4:** Commit `docs(commercial): pitch one-pager and 5min demo script`

**验收:** 他人可按脚本独立完成演示。

---

## Iteration 12 — 公网发布与冒烟收口（T+7h40 ~ 8h30）

**Files:**
- Create: `runtime_evidence/launch_smoke.md`
- Update: `doc/ilearn_public_url.txt`（新 URL）
- Optional: `scripts/launch_soft.sh` / `.ps1`

**Interfaces:**
- Smoke checklist: healthz · Landing · waitlist · demo student · parent summary · teacher tier · privacy · PDF export（若时间够）

- [ ] **Step 1:** `frontend` production build
- [ ] **Step 2:** 启动 API 托管 dist；开隧道（cpolar/cloudflared）
- [ ] **Step 3:** 按 checklist 打勾写入 `launch_smoke.md`
- [ ] **Step 4:** 失败项列入「明日债」而非偷偷扩大今晚范围
- [ ] **Step 5:** Commit `chore: soft-launch smoke evidence`

**验收:** 规格 §1 DoD 全绿或明示缺口 ≤2 且不影响主演示。

---

## Post-night（明确不今晚做）

1. 支付与发票  
2. 真实短信/邮件验证  
3. 多学校租户  
4. Enhanced KT 默认开  
5. 全学段内容扩张  

---

## Spec coverage check

| 规格要求 | 迭代 |
| --- | --- |
| 公网可演示 | 4, 6, 12 |
| 候补留资 | 2, 3 |
| 计时可信 | 5 |
| 家长可行动 | 7 |
| 教师下一步 | 8 |
| 隐私边界 | 9 |
| 不泄题初衷 | 1, 10 |
| 竞品叙事 | 1, 11 |
| 掌握度效果叙事 | 1, 6, 7 |
| Demo 脚本 | 11 |
| 冒烟证据 | 12 |

## Placeholder scan

无 TBD 核心步骤；支付等已列入 Post-night。

---

## Execution handoff

Plan saved. **推荐：Inline Execution（本会话按 Iteration 0→12 连续推进）**，因一晚时间盒不适合频繁切换上下文。

开始执行时从 **Iteration 0** 起，每轮结束做最小 commit（若用户未禁止 commit；默认计划含 commit，执行前若仓库策略需确认则以用户既有规则：仅在用户要求时 commit——**注意**：user rule says only commit when requested. 因此执行时 **跳过 commit 步骤**，改为本地保存；用户明确要求再提交）。
