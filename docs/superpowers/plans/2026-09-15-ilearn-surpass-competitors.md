# ILearn Surpass-All-Competitors Capability Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. **One iteration = one Capability Pillar (P#).** Do not mix pillars in one PR/session slice.

**Goal:** 在每个单点能力上达到并超过 12 家对照竞品的最佳水位（Win Bar），同时守住课标在环 / 不泄终答初衷。

**Architecture:** 旁路增强现有 MultiAgent + React 向导；每柱交付「水位对照表 + 代码 + 自动评测 + 5min 演示要点」。

**Tech Stack:** Python 3.11 · FastAPI · React/Vite/TS · Pytest/Vitest · 现有 SessionStore / GradingReceipt / Tutor / Evidence

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-15-ilearn-surpass-competitors-design.md`
- 初衷：课标在环 · 批改可审计 · 掌握度双轨 · 辅导不泄终答 · 试点诚实
- **禁止**用更快给终答来「超越」搜题竞品
- 一轮只做一个 Pillar（P1…P12）
- Wave-0（一竞品一轮叙事铺垫）已完成，见 `docs/commercial/OVERNIGHT_ROUNDS.md`；本计划从 **超越阶段** 开始

### File map（跨柱会反复触及）

| 路径 | 职责 |
| --- | --- |
| `ilearn/core/schemas.py` / `grading*` | 收据与证据 |
| `ilearn/agents/tutor.py` | 护栏 |
| `ilearn/core/audience_summary.py` | 家长/教师摘要 |
| `ilearn/api/app.py` | 对外 API |
| `frontend/src/components/*` | 各柱 UI |
| `docs/commercial/WIN_BARS.md` | 动态水位与达标记录 |
| `tests/eval_winbars/*` | 超越门禁评测 |

---

## Prep Task 0: Win Bar 记分板

**Files:**
- Create: `docs/commercial/WIN_BARS.md`
- Create: `tests/eval_winbars/README.md`

- [ ] **Step 1:** 将规格 §3 十二柱 Win Bar 抄入 `WIN_BARS.md`，增加列：`status: open|wip|pass`、`evidence_link`
- [ ] **Step 2:** README 说明：每柱合并前必须有对应 pytest/vitest 文件路径
- [ ] **Step 3:** Commit `docs: add win-bar scoreboard for surpass plan`

---

## Wave A — 夯实碾压基座

### Task A1 / Pillar P3: 苏格拉底护栏超越 Khanmigo（可测不泄题）

**Competitor waterline:** Khanmigo 伦理；反面 Photomath/Gauth 给答案  
**Win Bar:** Tutor 全路径对 fixture 零泄漏 `answer_key`；UI soft-exit；CI 门禁

**Files:**
- Modify: `ilearn/agents/tutor.py`
- Create: `tests/eval_winbars/test_p3_no_answer_leak.py`
- Modify: `frontend/src/components/TutorPanel.tsx`（若缺口）
- Test: 现有 `tests/test_tutor_agent.py` + 新评测

**Interfaces:**
- Produces: `assert_no_answer_leak(turn.message, answer_key) -> None`

- [ ] **Step 1:** 写失败测试：对带 `answer_key="3.6"` 的 item，跑 start→hint_1→hint_2→retry 失败→explain→done，所有 message 不含 `3.6`
- [ ] **Step 2:** 跑测确认若已通过则标记增强边界（含半角/空格变体）
- [ ] **Step 3:** 补强 `_build_explanation` / Guard：数字与归一化匹配红线
- [ ] **Step 4:** Vitest：soft-exit 后无「下一提示」
- [ ] **Step 5:** 更新 `WIN_BARS.md` P3=pass
- [ ] **Step 6:** Commit `test(p3): win-bar no-answer-leak gate for tutor`

---

### Task A2 / Pillar P2: 掌握度严谨超越小猿+松鼠

**Waterline:** 小猿掌握度分；松鼠细粒度黑盒  
**Win Bar:** 对外 API 同时返回 mastery、evidence_count、probe_gap、hint_solved_not_mastered

**Files:**
- Modify: `ilearn/core/audience_summary.py` 或新建 `ilearn/core/mastery_public.py`
- Modify: `GET /sessions/{id}/summary/student`（及 diagnosis enrichment）
- Modify: `frontend/src/components/StudentSummaryPanel.tsx`
- Create: `tests/eval_winbars/test_p2_mastery_rigor.py`

**Interfaces:**
- Produces: `MasteryPublicView { mastery_percent, evidence_count, probe_gap_count, discounted_hint_correct: int }`

- [ ] **Step 1:** 单测：构造「仅 hint 后做对」会话 → `discounted_hint_correct >= 1` 且不得把该 KP 标为 mastered
- [ ] **Step 2:** 实现聚合视图（只读 metadata/evidence_log）
- [ ] **Step 3:** 学生 UI 展示四元组（掌握度 / 证据 / probe 缺口 / 提示折扣）
- [ ] **Step 4:** WIN_BARS P2=pass；Commit `feat(p2): public mastery rigor surpasses single-score rivals`

---

### Task A3 / Pillar P1: 课标题级溯源超越「宣称同步」

**Waterline:** 讯飞区域同步叙事；Khanmigo 内容库  
**Win Bar:** 正式卷无 citation fail closed；UI 一键展开课标+例题来源

**Files:**
- Modify: `ilearn/core/assessment_paper_builder.py` / Assessment 校验
- Modify: `frontend/src/components/CitationPanel.tsx`
- Create: `tests/eval_winbars/test_p1_citation_fail_closed.py`

- [ ] **Step 1:** 测试：构造缺 `source_refs` 的 item → `revise_paper`/组卷拒绝或自动替换
- [ ] **Step 2:** 实现 fail closed（试点卷路径）
- [ ] **Step 3:** CitationPanel 展示 curriculum_objective_ids + textbook_chapter + example_stem（仍可隐藏 example_answer）
- [ ] **Step 4:** WIN_BARS P1=pass；Commit `feat(p1): citation fail-closed for pilot papers`

---

### Task A4 / Pillar P5: 批改收据对外超越黑盒批改

**Waterline:** 竞品几乎不公开 grader 版本  
**Win Bar:** 每题可查看/导出 GradingReceipt；教师「复核」页

**Files:**
- Locate existing receipt models under `ilearn/core/`
- Create: `ilearn/api` route `GET /sessions/{id}/grading-receipts`
- Create: `frontend/src/components/GradingReceiptPanel.tsx`
- Create: `tests/eval_winbars/test_p5_receipt_export.py`

- [ ] **Step 1:** 测试：批改后 receipts 长度 = grades 长度，含 grader_version 字段
- [ ] **Step 2:** API + 学情步 UI 面板
- [ ] **Step 3:** PDF 附录可选嵌入收据摘要
- [ ] **Step 4:** WIN_BARS P5=pass；Commit `feat(p5): expose grading receipts to beat black-box graders`

---

## Wave B — 角色闭环碾压

### Task B1 / Pillar P6: 家长行动超越「只有图表」

**Waterline:** 松鼠/讯飞家长看板  
**Win Bar:** 3 条行动每条绑定 KP + 可导出亲子题卡 PDF

**Files:**
- Modify: `ilearn/core/parent_action_summary.py`
- Create: `GET /sessions/{id}/export/parent-card.pdf`
- Modify: `ParentDashboard.tsx`
- Create: `tests/eval_winbars/test_p6_parent_actions_bound.py`

- [ ] **Step 1:** 测试：actions[*] 含 weak KP 子串；PDF 路由 200
- [ ] **Step 2:** 实现题卡 markdown→PDF
- [ ] **Step 3:** 家长端「导出今晚题卡」按钮
- [ ] **Step 4:** WIN_BARS P6=pass；Commit `feat(p6): parent action cards bound to weak KPs`

---

### Task B2 / Pillar P7: 教师一键分层出卷超越「建议文案」

**Waterline:** Century 干预建议；学而思看板  
**Win Bar:** `POST /teacher/tiers/assign` 生成三份巩固卷草稿并可绑定班级

**Files:**
- Modify: `ilearn/core/tier_suggest.py`
- Create: `ilearn/api/teacher_tiers.py`
- Modify: `TeacherDashboard.tsx`
- Create: `tests/eval_winbars/test_p7_tier_papers.py`

- [ ] **Step 1:** 测试：三档学生 → 三份 paper item 数 > 0 且难度配额不同
- [ ] **Step 2:** 实现出卷（复用 AssessmentAgent 巩固路径）
- [ ] **Step 3:** UI：「一键分层布置」调用 API 并展示回执
- [ ] **Step 4:** WIN_BARS P7=pass；Commit `feat(p7): one-click tiered practice assignment`

---

### Task B3 / Pillar P12: 错题资产超越作业帮错题本（仍不泄终答）

**Waterline:** 作业帮错题沉淀  
**Win Bar:** 错题本条目 = stem + steps + citation + evidence + 重练；默认无终答

**Files:**
- Create: `ilearn/core/error_notebook.py`
- Create: `GET /sessions/{id}/error-notebook`
- Modify: 学生/家长 UI
- Create: `tests/eval_winbars/test_p12_error_notebook.py`

- [ ] **Step 1:** 测试：notebook 条目不含 answer_key；含 rubric_steps
- [ ] **Step 2:** 实现聚合
- [ ] **Step 3:** UI 列表 + 导出
- [ ] **Step 4:** WIN_BARS P12=pass；Commit `feat(p12): error notebook without answer leak`

---

## Wave C — 体验与信任碾压

### Task C1 / Pillar P4: 分步对齐可视化超越 Photomath（合规版）

**Waterline:** Photomath 分步  
**Win Bar:** 学生作答步骤 vs rubric 逐步对齐（匹配/缺失/多余）；终答遮罩

**Files:**
- Create: `ilearn/core/step_align.py`
- Modify: `StepReviewList.tsx`
- Create: `tests/eval_winbars/test_p4_step_align.py`

- [ ] **Step 1:** 单测对齐算法（简单 token/行匹配即可）
- [ ] **Step 2:** UI 高亮匹配步
- [ ] **Step 3:** WIN_BARS P4=pass；Commit `feat(p4): step alignment viz without final answer`

---

### Task C2 / Pillar P8: 低龄负荷超越洋葱公平性

**Waterline:** 洋葱单题/先概念  
**Win Bar:** 移动单题 + 概念入口 + 计时排除系统暂停（已有则加固评测）

**Files:**
- Modify: `Assessment.tsx` / `useCountdown.ts`
- Create: `tests/eval_winbars/test_p8_timer_excludes_feedback.py`（前端 vitest）
- Optional: hint 用尽 → 概念卡

- [ ] **Step 1:** Vitest：pause 期间 seconds 不变
- [ ] **Step 2:** 移动端强制一题 + 概念卡 CTA
- [ ] **Step 3:** WIN_BARS P8=pass；Commit `feat(p8): cognitive load + fair timer win-bar`

---

### Task C3 / Pillar P9: 激活摩擦超越 Gauth/豆包（诚实版）

**Waterline:** 秒进对话  
**Win Bar:** ≤2 点击、≤60s 看到 P1/P2/P5 任一证据；脚本化冒烟

**Files:**
- Modify: `LandingPage.tsx`
- Create: `scripts/smoke_activation_60s.py`（API 级）
- Create: `docs/commercial/DEMO_60S.md`

- [ ] **Step 1:** 冒烟脚本：create demo → summary/parent 含 action_summary 或 citation 字段计时
- [ ] **Step 2:** Landing 主 CTA 去干扰
- [ ] **Step 3:** WIN_BARS P9=pass；Commit `feat(p9): sub-60s honest activation path`

---

### Task C4 / Pillar P10: 编排信任超越闭源黑盒与开源 Demo

**Waterline:** OpenMAIC 可观测；闭源不可见  
**Win Bar:** `GET /sessions/{id}/decision-log/summary` + Trust 页实时拉取 capabilities

**Files:**
- Modify: `TrustPage.tsx`
- Create: API summary endpoint
- Create: `tests/eval_winbars/test_p10_decision_summary.py`

- [ ] **Step 1:** 测试：summary 含 phases 列表与 agent 名
- [ ] **Step 2:** Trust 页 fetch 展示
- [ ] **Step 3:** WIN_BARS P10=pass；Commit `feat(p10): decision-log summary for trust win-bar`

---

## Wave D — 长期护城河

### Task D1 / Pillar P11: 陪伴连续性超越小精龙叙事

**Waterline:** 学而思长期 Agent  
**Win Bar:** 同昵称跨 session 合并下一挑战；7 日任务链 API

**Files:**
- Create: `ilearn/core/companion_continuity.py`
- Create: `GET /learners/{nickname}/continuity`
- Frontend：计划步展示连续天数
- Create: `tests/eval_winbars/test_p11_continuity.py`

- [ ] **Step 1–4:** TDD 实现 → WIN_BARS P11=pass → Commit `feat(p11): cross-session companion continuity`

---

### Task D2: 公开超越基准套件

**Files:**
- Create: `tests/eval_winbars/run_all.py`
- Modify: `VERSION.md` / CI 可选 job

- [ ] **Step 1:** 一键跑 P1–P12 门禁，输出 Markdown 报告到 `runtime_evidence/winbar_report.md`
- [ ] **Step 2:** README 徽章说明「单点能力门禁」
- [ ] **Step 3:** Commit `test: aggregate win-bar suite`

---

## Suggested calendar（非强制，供排期）

| 日序 | 柱 |
| --- | --- |
| D1 | P3, P2 |
| D2 | P1, P5 |
| D3 | P6, P7 |
| D4 | P12, P4 |
| D5 | P8, P9 |
| D6 | P10, P11 |
| D7 | 全量 win-bar suite + 演示录像 |

---

## Spec coverage

| Spec pillar | Task |
| --- | --- |
| P1 | A3 |
| P2 | A2 |
| P3 | A1 |
| P4 | C1 |
| P5 | A4 |
| P6 | B1 |
| P7 | B2 |
| P8 | C2 |
| P9 | C3 |
| P10 | C4 |
| P11 | D1 |
| P12 | B3 |
| 记分板/套件 | Prep, D2 |

## Placeholder scan

无 TBD 核心路径；支付/多租户仍排除。

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-09-15-ilearn-surpass-competitors.md`.

**推荐执行顺序：** Prep → A1(P3) → A2(P2) → A3(P1) → A4(P5) → Wave B → C → D。

**两种执行方式：** Subagent-Driven（每柱一个子代理）或本会话 Inline；默认从 **Task 0 + A1** 开始。
