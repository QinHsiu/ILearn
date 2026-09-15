# ILearn Overnight Commercial Plan — One Competitor Per Round

> **For agentic workers:** Execute rounds in order. **Each round may only absorb strengths from ONE named competitor.** Do not mix competitor scopes within a round.

**Goal:** 一晚完成软上线级商业化交付（可演示、可候补、初衷不破），通过 **12 轮「一竞品一轮」** 迭代把差异化打穿。

**Architecture:** FastAPI + React 向导旁路增强；不重写 MultiAgent 主链；Enhanced Flag 默认关。

**Tech Stack:** Python 3.11 · FastAPI · React/Vite/TS · Pytest/Vitest

## Global Constraints

- **初衷锚点：** 课标在环 · 批改可审计 · 掌握度双轨 · 辅导不泄终答 · 试点诚实（小学数学 4–6 · 北京·人教）
- **一轮一只竞品：** 本轮文案/代码/测试只能引用该竞品的优点吸收点
- **路径：** A+C 软上线（公网可后置；先做体验与叙事交付）
- **禁止：** 支付、多租户、全科假装商用、把产品改成搜题器

## Competitor Queue (12 rounds)

| Round | Competitor | Absorb (only this) | Deliverable |
| --- | --- | --- | --- |
| 1 | **Khanmigo** | 苏格拉底不给终答 + 伦理可见 | TutorPanel 伦理条 + soft-exit UI |
| 2 | **小猿 AI** | 掌握度北极星 | Landing/学生摘要「掌握度」主叙事强化 |
| 3 | **Photomath** | 分步可视化（不泄终答） | 错题复盘步骤展示增强 |
| 4 | **作业帮** | 反面：防搜题异化 | 显性「非搜题」护栏文案 + Guard 提示 |
| 5 | **科大讯飞** | 区域课标诚实 | 试点地区/课标徽章全链路 |
| 6 | **松鼠 AI** | 薄弱点粒度 + 家长指标 | 家长摘要薄弱点颗粒度 |
| 7 | **学而思/小精龙** | 长期陪伴与下一挑战 | Demo resume / 下一挑战强调 |
| 8 | **洋葱学园** | 低龄认知负荷 | 测评移动端单题聚焦（最小） |
| 9 | **Gauth** | 低摩擦进演示 | Landing CTA ≤2 步体验优化 |
| 10 | **Century 类** | 教师决策下一步 | 教师 next_step 可执行性 |
| 11 | **豆包爱学** | 深链低摩擦 | session 深链与角色入口打磨 |
| 12 | **OpenMAIC/DeepTutor** | 可审计编排信任 | decision_log/capabilities 对外可见一页 |

## File map (shared)

- `docs/commercial/OVERNIGHT_ROUNDS.md` — 本队列与验收
- Per-round touch files listed inside each round below

---

### Round 1: Khanmigo — Socratic ethics visible

**Competitor only:** Khanmigo  
**Files:**
- Modify: `frontend/src/components/TutorPanel.tsx`
- Modify: `frontend/src/api/client.ts` (`TutorTurn.action`)
- Modify: `frontend/src/components/TutorPanel.test.tsx`
- Modify: `frontend/src/styles.css` (tutor ethics)

**Accept:**
- UI 明示「引导思考，不直接给最终答案」
- `action === 'suggest_review'` 时展示柔性出口，并停止继续「要答案」式追问入口（禁用下一提示或改文案）

---

### Round 2: 小猿 — Mastery north star

**Competitor only:** 小猿  
**Files:** Landing + StudentSummaryPanel + optional student narrative copy  
**Accept:** 首屏与计划步「掌握度」为第一阅读顺序

---

### Round 3: Photomath — Step visualization without final answer

**Competitor only:** Photomath  
**Files:** App 错题复盘 / EvidenceChain / grade display  
**Accept:** 分步可见；终答默认遮罩或不出

---

### Round 4: 作业帮 — Anti search-engine

**Competitor only:** 作业帮  
**Files:** Landing + LegalPrivacy + Assessment focus copy  
**Accept:** 明确「不做拍照出答案」差异句

---

### Round 5: 讯飞 — Regional honesty badge

**Competitor only:** 科大讯飞  
**Files:** Landing + onboard/region display  
**Accept:** 「北京·人教 · 小学数学 4–6」徽章稳定出现

---

### Round 6: 松鼠 AI — Fine weak-point + parent metrics

**Competitor only:** 松鼠 AI  
**Files:** parent_action_summary + ParentDashboard  
**Accept:** 薄弱点命名可读、指标一眼可见

---

### Round 7: 学而思 — Companion continuity

**Competitor only:** 学而思/小精龙  
**Files:** demo deep link / StudentSummary next_challenge  
**Accept:** 下一挑战视觉权重提升

---

### Round 8: 洋葱学园 — Cognitive load

**Competitor only:** 洋葱学园  
**Files:** Assessment mobile single-item mode (minimal)  
**Accept:** 窄屏一次一题

---

### Round 9: Gauth — Frictionless demo

**Competitor only:** Gauth  
**Files:** LandingPage CTA layout  
**Accept:** 主 CTA 上方无多余打断

---

### Round 10: Century — Teacher decision

**Competitor only:** Century/Knewton  
**Files:** TeacherDashboard next_step  
**Accept:** 分层建议可被教师 5 秒读懂

---

### Round 11: 豆包爱学 — Deep link polish

**Competitor only:** 豆包爱学  
**Files:** demo links / query resume  
**Accept:** 三角色深链稳定

---

### Round 12: OpenMAIC/DeepTutor — Auditable trust page

**Competitor only:** 开源同行  
**Files:** `?trust=1` 或 capabilities 展示页  
**Accept:** 展示编排可观测/课标在环证据点

---

## Commercial DoD (night end)

1. 12 轮中至少完成 **R1–R6** 代码+测试；R7–R12 能完成则继续，否则写入「次日债」但不破坏初衷  
2. Demo 三角色可讲完故事  
3. Waitlist + healthz 可用（已有则保持）  
4. 文案无「秒出答案/代写/全科商用」

## Spec refs

- Intent: README / INTRODUCTION  
- Prior research: `docs/commercial/COMPETITORS.md`
