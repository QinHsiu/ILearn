# React + Vite + FastAPI Web UI Design

**Date:** 2026-08-13  
**Status:** Approved  
**Branch:** feature/edition0813-p0-p1 (or follow-up)

## Goal

Replace Streamlit as the sole teaching Web UI with **React 18 + TypeScript + Vite**, talking to the existing FastAPI orchestrator over HTTP.

## Decisions locked

- Framework: React + Vite (TS)
- Dev: dual ports — Vite `:5173` + FastAPI `:8000` with proxy
- Prod: FastAPI serves `frontend/dist` SPA; `/docs` remains Swagger
- Streamlit: deprecated as primary entry (code may remain temporarily)

## Layout

```
frontend/
  package.json
  vite.config.ts          # proxy /sessions → :8000
  index.html
  src/
    main.tsx
    App.tsx               # wizard shell
    api/client.ts
    steps/Onboard.tsx
    steps/Assess.tsx
    steps/Diagnosis.tsx
    steps/Plan.tsx
    themes.css            # CSS variables; band×gender accents
    styles.css
```

## Wizard parity (MVP)

1. Onboard — region, grade, age, nickname, gender → POST `/sessions` + `/assessment`
2. Assess — answer items → POST `/submit` + `/run` (item_meta optional `{}`)
3. Diagnosis — mastery, abilities, wrong-item source_refs expanders
4. Plan — learning plan markdown / structured fields from report session

Image OCR: placeholder / deferred.

## FastAPI changes

- CORS: add `http://localhost:5173`, `http://127.0.0.1:5173`
- If `frontend/dist` exists: mount StaticFiles + SPA fallback on `/` (API routes take precedence); else keep redirect to `/docs`

## Out of scope

- Supabase / Vercel fullstack-deploy pipeline
- Rewriting Agent business logic
