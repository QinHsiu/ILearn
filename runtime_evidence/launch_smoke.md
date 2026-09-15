# Soft-launch smoke checklist (Edition 0914) — audit 2026-09-14 23:59

## Automated (verified this check)

- [x] waitlist + healthz pytest
- [x] commercial soft-launch pytest (parent/tutor/tier)
- [x] summary API (404 + action_summary + tier + mastery_percent)
- [x] TutorPanel / StepReviewList / Landing / StudentSummary vitest (14)

## 12 competitor rounds (code presence)

- [x] R1 Khanmigo — TutorPanel ethics + soft-exit
- [x] R2 小猿 — Landing 掌握度主叙事 + student mastery strip
- [x] R3 Photomath — StepReviewList
- [x] R4 作业帮 — 非搜题/不拍照出答案文案
- [x] R5 讯飞 — pilot-badge
- [x] R6 松鼠 — parent_action_summary 颗粒度
- [x] R7 学而思 — summary-block-challenge
- [x] R8 洋葱 — assessment-one-at-a-time (mobile)
- [x] R9–11 — Demo/教师 next_step/深链（既有能力确认）
- [x] R12 OpenMAIC — TrustPage `?trust=1`

## Not done (by design or deferred)

- [ ] 公网隧道 / 正式域名上线
- [ ] 支付 / 多租户
- [ ] 人工全路径浏览器走查（三角色 Demo 手点）
