# Edition 0901_3 Design — Student Flow UI Polish (Swiss / Klein Blue)

**Date:** 2026-09-01  
**Status:** Ready for user review (self-reviewed)  
**Source:** User request — student UI elegance (assessment-first); scope **B** full student flow; depth **B** structural small changes + CSS  
**Baseline:** Edition 0901_2; visual system `frontend/DESIGN.md` + `deck-swiss-international` Klein Blue  
**Skills:** brainstorming → DESIGN.md / Swiss International tokens (not a new palette)

## Goal

Make the **student wizard** (建档 → 测评 → 学情/Tutor → 计划) feel as calm and precise as the Landing: strong type hierarchy, hairline geometry, single accent `#002FA7`, square controls — especially the assessment surface — without changing assessment/tutor API behavior.

## Scope

**In:**

1. Shared student shell chrome + step indicator aligned to DESIGN.md tokens
2. Onboarding (建档) form density and primary/secondary button rhythm
3. Assessment header three-layer structure (phase / counter / curriculum); ProgressDots as square index; single-item focus card; full-row choice targets; action bar rhythm
4. Diagnosis step: elevate `TutorPanel` as「苏格拉底助教」block (existing tutor APIs)
5. Plan step: align `StudentSummaryPanel` + plan markdown to the same shell spacing
6. CSS in `styles.css` (and minimal component class hooks); preserve `--radius: 0`

**Out:**

- Landing / teacher / parent dashboard redesign
- New color system, gradients, shadows, rounded UI
- New routes / react-router
- Assessment adaptive logic, grading, or tutor backend changes
- Replacing `TutorPanel` with a separate `SocraticPanel` app (reuse copy/style only)

## Architecture (approved §1)

| Surface | Change |
| --- | --- |
| Shell | `.student-shell` + `.student-chrome` (`学生学习 / NEXT STEP`) + `.student-steps` |
| 建档 | Grouped fields, primary CTA, secondary back/history |
| 测评 | `.assess-phase` · `.assess-counter` · chapter/meta; square ProgressDots; stem emphasis; choice rows |
| 学情 | Table scanability; Tutor titled block |
| 计划 | Summary + markdown share shell gutters |

## Tokens / classes / tests (approved §2)

### Tokens (existing — enforce)

```text
--il-blue: #002FA7
--il-paper: #FAFAF8
--il-ink: #0A0A0A
--il-muted: #5F6368
--il-line: #C9CCD2
--il-soft: #EEF1F7
--radius: 0
Fonts: Inter Tight (display), Inter + Noto Sans SC (body), JetBrains Mono (labels/counters)
```

### Class map

| Class | Role |
| --- | --- |
| `.student-shell` | Outer student wizard width + paper |
| `.student-chrome` | Eyebrow + optional nickname |
| `.student-steps` | Four steps; current = accent underline |
| `.assess-phase` | Mono 11px: ANCHOR / FULL (or 中文短标签) |
| `.assess-counter` | Mono `n / N` |
| `.item-card` / `.item-stem` | Focus card; stem ~1.25–1.4rem weight 600 |
| `.choices label` | Full-row hairline hit target; selected = soft + 3px left accent |
| `.tutor-panel` | Title 苏格拉底助教 + turns + input |

### Spacing

Shell vertical ~2rem; head→items 1.5rem; choice gap 0.5rem; actions bar topped by hairline.

### Files

- Modify: `frontend/src/App.tsx`, `pages/Assessment.tsx`, `components/TutorPanel.tsx`, optionally `ProgressDots.tsx`, `StudentSummaryPanel.tsx`
- Modify: `frontend/src/styles.css`
- Tests: Assessment structure (phase/counter); TutorPanel heading; existing resume/auth smoke green

### Errors / a11y

- Keep `aria-live` errors
- Focus ring: 2px `--il-blue` + 2px offset
- `prefers-reduced-motion: reduce` — no motion beyond 180ms opacity/color
- Min 44px touch targets on primary actions and choice rows

## Implementation task order

1. Student shell + steps in `App.tsx` + CSS
2. 建档 panel polish
3. Assessment header + ProgressDots + item/choices + actions
4. TutorPanel elevation on diagnosis step
5. Plan / StudentSummary alignment
6. Vitest updates + VERSION note (Edition 0901_3 UI)

## Success criteria

- [ ] Student flow visually consistent with Landing tokens (no new palette)
- [ ] Assessment readable: phase, counter, stem, choices clearly hierarchical
- [ ] Tutor block labeled and discoverable on 学情 step
- [ ] Vitest green for touched surfaces; no API contract changes
