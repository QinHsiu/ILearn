# Edition 0909_6 Thin UI — Enhanced Student Panel Design

**Date:** 2026-09-10  
**Status:** Approved for implementation planning  
**Scope:** Thin frontend only — SVG radar + weak concepts + emotion cards on teacher/parent dashboard and student session. No path/roles/reflection/trend backends.

## Goal

Surface existing `?enhanced=` five-dim profile data in the UI when explicitly enabled, without new chart libraries or new API routes.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Product slice | A — thin frontend (no Phase 2–4 APIs) |
| Mount points | C — both `DashboardDetail` and `StudentSummaryPanel`, shared panel |
| Charts | Pure SVG (from `doc/chart.txt`); no echarts |
| Implementation style | Port `chart.txt` structure; adapt to existing `api/client` + CSS modules |
| Frontend flag | `VITE_ENHANCED_UI` default false (`ENHANCED_UI_ENABLED`) |
| Backend data | Existing summary endpoints + `ENABLE_ENHANCED_API`; field `enhanced_profile` |

## Architecture

### Flags

- **UI:** `VITE_ENHANCED_UI=true` → `ENHANCED_UI_ENABLED` in `frontend/src/config/enhanced.ts`.
- **Data:** Backend still requires `ENABLE_ENHANCED_API` (and profile population via PROFILE/AGENTS/KT as already designed). UI flag does not create data.

When UI flag is off: no enhanced requests from the new panel path; dashboard/student UI identical to today.

### Components

| Unit | Responsibility |
|------|----------------|
| `KnowledgeRadar` | SVG radar from `knowledge_mastery`; prefer weakest first; &lt;3 keys → downgrade text |
| `WeakConceptsCard` | Chip list; student copy「待加强」/ teacher「薄弱知识点」 |
| `EmotionCard` | Emotion + learning style + optional overall mastery % |
| `EnhancedStudentPanel` | Fetch + compose; flag off / no profile → `null`; **show minimal loading** while fetch in flight |

### Data flow

1. Panel receives `sessionId` + `viewMode: 'student' | 'teacher'`.
2. Calls existing client methods with `enhanced: true`:
   - student surface → `GET /sessions/{id}/summary/student?enhanced=true`
   - teacher surface → `GET /sessions/{id}/summary/teacher?enhanced=true`
   - parent dashboard detail → `GET /sessions/{id}/summary/parent?enhanced=true`
3. Reads **`enhanced_profile`** (not `profile`). Missing/falsey → render nothing after load.
4. Errors → silent null (no blocking error banner on dashboard).

### Mounts

- `DashboardDetail`: after main detail content; `sessionId={detail.session_id}`; `viewMode="teacher"` for teacher surface, keep teacher weak-concept copy for parent surface as well (or pass `viewMode="teacher"` for both adult dashboards — adult wording「薄弱知识点」).
- `StudentSummaryPanel`: below existing summary grid; `viewMode="student"`.

### Styling

- **No Tailwind.** Use CSS modules: single `enhanced.module.css` shared by Enhanced components (avoid global `*.css` pollution).
- Visual tokens aligned with `chart.txt` (blue radar fill `#4285f4`, weak chips red-tint) but class names from the module.

### Loading UX (approved addition)

While `ENHANCED_UI_ENABLED` and request in flight, render a minimal placeholder, e.g. panel with text「加载画像…」, to avoid layout jump/blank flash. After settle: either full panel or `null`.

## File checklist

| Path | Role |
|------|------|
| `frontend/src/config/enhanced.ts` | `ENHANCED_UI_ENABLED` |
| `frontend/src/components/Enhanced/KnowledgeRadar.tsx` | SVG radar |
| `frontend/src/components/Enhanced/WeakConceptsCard.tsx` | Weak list |
| `frontend/src/components/Enhanced/EmotionCard.tsx` | Emotion / style |
| `frontend/src/components/Enhanced/EnhancedStudentPanel.tsx` | Orchestrator + loading |
| `frontend/src/components/Enhanced/enhanced.module.css` | Shared module styles |
| `frontend/src/components/Enhanced/index.ts` | Barrel export |
| `frontend/src/api/client.ts` | Types + `enhanced` query on summary getters |
| `frontend/src/components/DashboardDetail.tsx` | Mount |
| `frontend/src/components/StudentSummaryPanel.tsx` | Mount |
| `frontend/.env.example` | `VITE_ENHANCED_UI=false` |
| `frontend/src/components/Enhanced/*.test.tsx` | Component tests |

## Testing

1. UI flag off → panel null / no enhanced query from panel.
2. Flag on + mock without `enhanced_profile` → null after load.
3. Flag on + full profile → radar + weak + emotion; student vs teacher weak copy.
4. Mastery keys &lt; 3 → radar downgrade copy.
5. Loading state visible before resolve (assert placeholder text).
6. Regression: existing `StudentSummaryPanel` / dashboard tests still pass.

## Acceptance

| Scenario | Expected |
|----------|----------|
| `VITE_ENHANCED_UI=false` | No new UI |
| UI on + slow API | Shows「加载画像…」then content or null |
| UI on + no `enhanced_profile` | Null, no crash |
| UI on + profile with ≥3 KPs | Radar + cards |
| UI on + &lt;3 KPs | Downgrade radar message |
| Student vs teacher | Copy differs for weak concepts |

## Non-goals

- echarts / Tailwind
- Path planner, multi-role bubbles, reflection modal, mastery trend
- New FastAPI routes (`enhanced_routes.py`)
- Fictional `/dashboard/student/{id}/summary` URL from early drafts

## Coding-draft adaptations (`doc/chart.txt`)

- Replace Tailwind classes with `enhanced.module.css`.
- Use `sessionId` + existing summary endpoints; parse `enhanced_profile`.
- Keep loading placeholder (above).
- Prefer `api` client over raw `fetch` for auth/base URL consistency.
