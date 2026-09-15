# Login and Dashboard Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix role dashboard API failures and add a polished role-selection/login experience without changing the student workflow.

**Architecture:** Add a small FastAPI auth router backed by environment-configured demo credentials. Add typed frontend login/landing pages and route them from `App.tsx`; proxy `/auth` and `/dashboard` through Vite. Reuse existing dashboard APIs and relationship data.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Vite, Vitest, pytest.

## Global Constraints

- Student mode remains the default when no login or dashboard query is present.
- Passwords are never hard-coded in frontend code or returned by the API.
- This slice provides demo authentication only; it does not introduce JWT, cookies, registration, or production authorization.
- Existing dashboard data contracts and relationship semantics remain unchanged.
- No new external dependencies.
- All tests must run on Windows PowerShell and POSIX-compatible CI environments.

---

### Task 1: Backend demo login and dashboard proxy regression

**Files:**
- Create: `ilearn/api/auth.py`
- Modify: `ilearn/api/app.py`
- Modify: `.env.example`
- Modify: `frontend/vite.config.ts`
- Test: `tests/test_auth_api.py`
- Test: `tests/test_vite_proxy.py`

**Interfaces:**
- `POST /auth/login` accepts `{ "role": "parent" | "teacher", "username": str, "password": str }`.
- Successful response is `{ "role": str, "user_id": str }`.
- `create_auth_router(credentials)` produces the auth router.
- Vite proxies `/auth` and `/dashboard` to the configured API target.

- [ ] **Step 1: Write failing backend tests**

Add tests for valid parent and teacher credentials, invalid password (401),
invalid role (400), and route registration through `create_app`.

- [ ] **Step 2: Run backend tests and verify failure**

Run `python -m pytest tests/test_auth_api.py -q`; expected failure is missing
auth route/module.

- [ ] **Step 3: Implement minimal auth router**

Use Pydantic request/response models and environment-derived credential values.
Compare the selected role's username/password and return only role/user_id.

- [ ] **Step 4: Add app wiring and proxy entries**

Load six `ILEARN_*` variables with development defaults, include the auth router,
and add `/auth` and `/dashboard` proxy entries beside `/sessions`.

- [ ] **Step 5: Verify**

Run `python -m pytest tests/test_auth_api.py tests/test_dashboard_api.py -q`
and `python -m pytest tests/test_vite_proxy.py -q`.

- [ ] **Step 6: Commit**

Commit as `feat: add demo role login and dashboard proxy`.

### Task 2: Landing and login frontend

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/LandingPage.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/auth.test.tsx`

**Interfaces:**
- `authApi.login(role, username, password)` returns `{ role, user_id }`.
- Login success redirects to `?role=parent&user=<id>` or
  `?role=teacher&user=<id>`.
- Landing cards link to `?login=1&role=parent` and
  `?login=1&role=teacher`.

- [ ] **Step 1: Write failing frontend tests**

Assert landing renders both role cards, login failure shows API detail, valid
login updates the URL with role/user, and no query still renders the student
heading.

- [ ] **Step 2: Run focused tests and verify failure**

Run `npm test -- --run src/auth.test.tsx`; expected failure is missing pages/API.

- [ ] **Step 3: Implement typed auth client and pages**

Use existing `request` behavior, controlled fields, role-specific labels, loading
state, and visible error state. Do not put credential defaults in TypeScript.

- [ ] **Step 4: Route from App**

Use `login=1` for login and render landing for the empty/default entry while
preserving the existing student flow behind an explicit student action.

- [ ] **Step 5: Verify**

Run `npm test -- --run src/auth.test.tsx` and `npm run build`.

- [ ] **Step 6: Commit**

Commit as `feat: add role landing and login screens`.

### Task 3: Dashboard visual polish and integration

**Files:**
- Modify: `frontend/src/pages/DashboardHome.tsx`
- Modify: `frontend/src/pages/ParentDashboard.tsx`
- Modify: `frontend/src/pages/TeacherDashboard.tsx`
- Modify: `frontend/src/dashboard.css`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/dashboard.test.tsx`

- [ ] **Step 1: Add failing UI assertions**

Cover role badge/header, readable empty/error states, responsive entry classes,
and dashboard action labels.

- [ ] **Step 2: Implement visual changes**

Use shared card styles, role-aware header/back link, clearer primary/secondary
actions, consistent spacing, and mobile layout. Keep API calls and query-state
behavior intact.

- [ ] **Step 3: Verify**

Run all frontend tests and build.

- [ ] **Step 4: Commit**

Commit as `style: polish role dashboards`.

### Task 4: Full verification and review

**Files:**
- No production changes unless a directly introduced test failure requires one.

- [ ] **Step 1: Run backend suite**

Run `python -m pytest -q`; record pass/fail and warnings.

- [ ] **Step 2: Run frontend suite and build**

Run `npm test -- --run` and `npm run build` from `frontend`.

- [ ] **Step 3: Inspect diff**

Run `git diff --check` and confirm no secrets or `.env` files are staged.

- [ ] **Step 4: Review**

Confirm student mode remains functional, passwords are not exposed, and
dashboard requests use the Vite proxy in development.
