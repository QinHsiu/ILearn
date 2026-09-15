# ILearn A→B/C Why-Use Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先打满三角色激活（≤2 点击 / ≤60s 见证据），再补家长行动锤与教师闭环锤，守住不泄终答初衷。

**Architecture:** 前端 Landing/三角色 CTA + `/quality-gates` 首屏可见；后端激活冒烟脚本写 `runtime_evidence`；家长结束页 PDF CTA + 收据白话；教师干预名单直达布置回执。

**Tech Stack:** FastAPI · React/Vite · Pytest · Vitest · 现有 demo session API

## Global Constraints

- 课标在环 · 不泄终答 · 证据化掌握度 · 试点诚实（小学数学 4–6 · 北京·人教）
- 不做：支付、多租户、以更快给终答换转化
- 规格：`docs/superpowers/specs/2026-09-15-ilearn-three-role-why-use-design.md`

---

## File map

| File | Responsibility |
| --- | --- |
| `frontend/src/pages/LandingPage.tsx` | 雇佣文案 + 质量门条 + 三角色一键 Demo |
| `frontend/src/pages/LandingPage.test.tsx` | Landing 文案/门禁测试 |
| `scripts/smoke_activation_roles.py` | 三角色 API 激活计时证据 |
| `runtime_evidence/activation_why_use.md` | 记录结果 |
| `frontend/src/App.tsx` / report 区 | 学生结束：亲子题卡/重练 CTA |
| `frontend/src/components/GradingReceiptPanel.tsx` | 收据白话 |
| `frontend/src/pages/ParentDashboard.tsx` | 周证据条 + PDF |
| `frontend/src/pages/TeacherDashboard.tsx` | 干预→布置；回执展示 |
| `tests/eval_winbars/test_p9_activation.py` | P9 激活门禁 |

---

### Task A1: Landing 雇佣文案 + 质量门首屏

- [x] 改 roleCards / hero 为 Why-Use 文案（学生敢问、家长今晚三件事、教师可布置）
- [x] Landing 拉取 `/quality-gates` 显示 enforced 摘要 + 链到 `?trust=1`
- [x] Vitest 断言雇佣关键词与质量门区块
- [x] 跑 `npm test -- LandingPage`

### Task A2: 三角色激活冒烟证据

- [x] `scripts/smoke_activation_roles.py`：demo session → student mastery/receipt、parent summary、teacher tier 各路径计时
- [x] 失败条件：任一角色 >60s 或缺证据字段
- [x] 写 `runtime_evidence/activation_why_use.md`
- [x] `test_p9_activation.py` 校验脚本存在且关键断言字符串

### Task B1: 家长行动锤

- [x] 学生报告结束页：导出亲子题卡 PDF 按钮（有 sessionId）
- [x] GradingReceiptPanel：白话「如何复核」一句
- [x] ParentDashboard：证据条数 / probe 缺口（若 summary 有则展示，否则从 mastery public）
- [x] 相关 vitest 或轻量 pytest

### Task C1: 教师闭环锤

- [x] 干预名单按钮改为「布置巩固」并调用 `assignTierPapers`
- [x] 布置成功后展示回执摘要（题量/时间）
- [x] 教师概览展示最近 `tier_assignment_receipt`（若 session 有）
- [x] 轻量测试（题级课标预览 vitest）

### Task Z: 验收

- [x] `pytest tests/eval_winbars -q`
- [x] 更新 `docs/commercial/WIN_BARS.md` P9 与三端 Why 备注
