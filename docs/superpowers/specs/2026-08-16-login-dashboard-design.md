# Login and dashboard polish

**Date:** 2026-08-16
**Status:** Approved

## Context

The existing student flow is the default application entry. Parent and teacher
dashboards are selected by query parameters and call `/dashboard` APIs. The
frontend dev proxy currently omits `/dashboard`, so role entry requests do not
reach FastAPI. The role links and dashboards also need a clearer visual hierarchy.

## Goals

- Add a unified role login screen with role, account, and password fields.
- Validate demo accounts on the backend using environment variables, never
  hard-code passwords in the frontend.
- Redirect successful parent/teacher login to the existing role dashboards.
- Add `/dashboard` and `/auth` Vite proxy entries.
- Improve role entry and dashboard visual presentation without changing student
  workflow or relationship semantics.
- Convert API failures into visible, human-readable UI errors.

## Demo authentication boundary

This is lightweight demo authentication, not production identity management.
The backend reads:

- `ILEARN_PARENT_USERNAME`
- `ILEARN_PARENT_PASSWORD`
- `ILEARN_PARENT_USER_ID`
- `ILEARN_TEACHER_USERNAME`
- `ILEARN_TEACHER_PASSWORD`
- `ILEARN_TEACHER_USER_ID`

Defaults are development-only values documented in `.env.example`. The login
response contains only `role` and `user_id`; passwords are never returned.
No session cookie, token, password hashing, registration, or authorization
system is introduced in this slice.

## Architecture

- `ilearn/api/auth.py` owns the login request/response models and a router
  factory that receives environment-derived demo credentials.
- `ilearn/api/app.py` loads credentials once while creating the app and includes
  the auth router.
- `frontend/src/pages/LoginPage.tsx` owns role selection and login form state.
- `frontend/src/pages/LandingPage.tsx` owns polished entry cards and links to
  the login page.
- `frontend/src/App.tsx` routes `?login=1` to login and retains student default.
- `frontend/src/api/client.ts` adds typed login calls.
- `frontend/src/dashboard.css` and `frontend/src/styles.css` provide shared
  responsive card, navigation, and form styling.
- `frontend/vite.config.ts` proxies `/auth` and `/dashboard` to FastAPI.

## Error handling

- Missing or invalid credentials return HTTP 401 with a generic message.
- Missing/invalid role returns HTTP 400.
- Frontend displays login/API errors in an error panel.
- Dashboard list/detail failures remain visible and never become uncaught
  promise rejections.

## Testing

- Backend tests cover valid parent/teacher login, invalid password, invalid role,
  and app route registration.
- Frontend tests cover landing entry cards, login success/failure, and preserving
  the student default route.
- Vite config is checked for both proxy paths.
- Full Python tests, frontend tests, and production build must pass.

## Non-goals

- Production authentication, JWT/session management, database users, invitations,
  password reset, or access control beyond demo credential selection.
- Changes to student assessment, diagnosis, relationship storage, or dashboard
  data contracts.
