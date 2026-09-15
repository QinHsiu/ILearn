# Edition 0901_3 Student Flow UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the student wizard (建档 → 测评 → 学情/Tutor → 计划) to match Landing Swiss / Klein Blue tokens with light structural markup — especially assessment hierarchy — without changing APIs or adaptive logic.

**Architecture:** Wrap `StudentApp` content in `.student-shell`; refine chrome/stepper; restructure Assessment header (phase / counter / meta); square ProgressDots; choice-row hit targets; elevate TutorPanel title; align plan/summary spacing via CSS + minimal class hooks.

**Tech Stack:** React 19, existing `styles.css` tokens (`--il-*`), Vitest + Testing Library.

## Global Constraints

- Visual system locked to `frontend/DESIGN.md` / Klein Blue: `#002FA7`, paper `#FAFAF8`, `--radius: 0`, no gradients/shadows/rounded pills.
- Fonts: Inter Tight / Inter + Noto Sans SC / JetBrains Mono.
- Scope = **student flow only**; no Landing/teacher/parent redesign.
- No API / adaptive / tutor backend changes; Tutor still uses `tutorStart` / `tutorHint`.
- Do **not** commit `doc/` or `docs/`; update `VERSION.md` only at end.
- TDD where new assertions are specified; keep existing Assessment/auth/resume tests green.
- Prefer CSS + small JSX hooks over large rewrites.

## File Structure

| Path | Responsibility |
| --- | --- |
| `frontend/src/App.tsx` | `.student-shell`, chrome, stepper classes, 建档/学情/计划 wrappers |
| `frontend/src/pages/Assessment.tsx` | Phase / counter / stem structure |
| `frontend/src/components/ProgressDots.tsx` | Accessible square index (visible number optional) |
| `frontend/src/components/TutorPanel.tsx` | 「苏格拉底助教」title block |
| `frontend/src/components/StudentSummaryPanel.tsx` | Optional shell-aligned class |
| `frontend/src/styles.css` | All new/updated student + assessment styles |
| `frontend/src/pages/Assessment.test.tsx` | Phase/counter assertions |
| `frontend/src/components/TutorPanel.test.tsx` | Create if missing — heading visible |
| `VERSION.md` | Edition 0901_3 UI note |

---

### Task 1: Student shell + chrome + stepper

**Files:**
- Modify: `frontend/src/App.tsx` (StudentApp return root)
- Modify: `frontend/src/styles.css`
- Test: extend `frontend/src/auth.test.tsx` or `App.studentResume.test.tsx` lightly — assert `学生学习 / NEXT STEP` still present (already may exist)

**Interfaces:**
- Produces: root `<div className="app-shell student-shell">`; header uses `.student-chrome` with eyebrow mono + brand; nav uses `.student-steps` (keep `aria-label="向导步骤"`); step items `.student-step` + `.is-active` / `.is-done`

- [ ] **Step 1: Write / adjust failing assertion**

In `App.studentResume.test.tsx` or a tiny new `StudentShell.test` via rendering Student path: expect document to contain role/text for NEXT STEP and nav `向导步骤`. If already present, add expectation that the stepper container has class including `student-steps` after implementation — for RED, assert `document.querySelector('.student-shell')` is null first by writing the test expecting it present.

```tsx
// In App.studentResume success path after plan loads, or a dedicated mount:
expect(document.querySelector('.student-shell')).toBeTruthy()
expect(screen.getByRole('navigation', { name: '向导步骤' })).toHaveClass('student-steps')
```

- [ ] **Step 2: Run test — expect FAIL** (`.student-shell` missing)

- [ ] **Step 3: Implement shell markup + CSS**

```tsx
<div className="app-shell student-shell">
  <header className="student-chrome">
    <p className="student-chrome-eyebrow">ILearn / STUDENT</p>
    <h1 className="brand">ILearn</h1>
    <h2 className="student-mode">学生学习 / NEXT STEP</h2>
    {/* nickname line if present */}
  </header>
  <nav className="stepper student-steps" aria-label="向导步骤">...</nav>
  ...
</div>
```

CSS: max-width ~1100px centered; paper bg; eyebrow JetBrains Mono 0.7rem; active step `border-bottom: 2px solid var(--il-blue)`; `border-radius: 0` everywhere touched.

- [ ] **Step 4: Run focused vitest — PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/styles.css frontend/src/App.studentResume.test.tsx
git commit -m "style(student): add Swiss student-shell chrome and steps"
```

---

### Task 2: 建档 form polish

**Files:**
- Modify: `frontend/src/App.tsx` (step 0 panel)
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: step 0 section `className="panel student-panel student-onboard"`; form fields keep ids; primary submit uses `.btn`; secondary actions unchanged functionally

- [ ] **Step 1: Assert onboard panel class in a small test** (or skip dedicated test if covered by shell — prefer one assertion in existing auth/student test for heading 建档 + button 开始测评)

- [ ] **Step 2–4: CSS for `.student-onboard` — field labels muted, inputs hairline, gap 1rem; no logic change; commit**

```bash
git commit -m "style(student): polish onboarding form density"
```

---

### Task 3: Assessment header + ProgressDots + item/choices

**Files:**
- Modify: `frontend/src/pages/Assessment.tsx`
- Modify: `frontend/src/components/ProgressDots.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/pages/Assessment.test.tsx`

**Interfaces:**
- Assessment head must render:
  - `.assess-phase` text: `锚点测评` phase → visible label `锚点` or `ANCHOR`; full → `完整` / `FULL` (prefer Chinese short: `锚点` / `完整` for a11y)
  - `.assess-counter` text matching `/1\s*\/\s*1/` on anchor fixture (1 item) or `1 / 20` after continue
  - `.item-stem` on stem paragraph
- ProgressDots buttons: square (CSS), `aria-label={`第 ${idx+1} 题`}` (improve from title-only)

- [ ] **Step 1: Extend Assessment.test.tsx**

```tsx
it('shows phase label and question counter on anchor paper', async () => {
  vi.mocked(api.adaptiveStart).mockResolvedValue(ANCHOR_START)
  render(
    <Assessment
      sessionId="s1"
      profile={{ region: 'beijing', grade: 5, age: 11 }}
      onComplete={vi.fn()}
    />,
  )
  expect(await screen.findByText('锚点测评')).toBeInTheDocument()
  // After polish, also:
  expect(screen.getByText(/1\s*\/\s*1/)).toBeInTheDocument()
  expect(screen.getByText('1+1=?')).toBeInTheDocument()
})
```

Adjust if phase label stays as h2 `锚点测评` — counter is the new required signal.

- [ ] **Step 2: Run — FAIL on counter if not present**

- [ ] **Step 3: Implement Assessment head**

```tsx
<div className="assess-head">
  <p className="assess-phase">{phase === 'anchor' ? '锚点' : '完整'}</p>
  <p className="assess-counter" aria-live="polite">
    {String(currentIndex + 1).padStart(2, '0')} / {String(paper.items.length).padStart(2, '0')}
  </p>
  <h2>{phase === 'anchor' ? '锚点测评' : '完整测评'}</h2>
  {/* chapter banner + lede unchanged */}
</div>
```

Stem: `<p className="item-stem">`. Choices: ensure `<label className="choice-row">`. ProgressDots: add `aria-label={`第 ${idx + 1} 题`}`.

CSS: `.assess-phase` / `.assess-counter` mono; `.item-stem` 1.3rem/600; `.choice-row` full-width padding min-height 44px; selected `box-shadow: inset 3px 0 0 var(--il-blue); background: var(--il-soft)`; `.progress-dot` width/height 12–14px square, current = blue fill.

- [ ] **Step 4: Run Assessment tests — PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "style(assessment): Swiss phase counter, stem, and choice rows"
```

---

### Task 4: TutorPanel elevation on 学情 step

**Files:**
- Modify: `frontend/src/components/TutorPanel.tsx`
- Create: `frontend/src/components/TutorPanel.test.tsx` (if none)
- Modify: `frontend/src/styles.css`
- Optionally wrap in `App.tsx` with `<section className="student-tutor-block" aria-label="苏格拉底助教">`

**Interfaces:**
- Visible heading text exactly `苏格拉底助教`
- Start button remains; turns styled as `.tutor-turn`

- [ ] **Step 1: Failing test**

```tsx
render(<TutorPanel sessionId="s1" itemId="q1" />)
expect(screen.getByRole('heading', { name: '苏格拉底助教' })).toBeInTheDocument()
```

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Add `<h3>苏格拉底助教</h3>` + lede one line; CSS hairline panel**

- [ ] **Step 4: PASS + commit**

```bash
git commit -m "style(tutor): elevate Socratic tutor panel on diagnosis step"
```

---

### Task 5: Plan step + StudentSummary alignment

**Files:**
- Modify: `frontend/src/App.tsx` (step 3 section classes)
- Modify: `frontend/src/components/StudentSummaryPanel.tsx` (root class `student-summary-panel`)
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Step 3 section: `panel student-panel student-plan`
- Summary grid uses existing summary-block; ensure no rounded cards; spacing 1.5rem under chrome

- [ ] **Steps: CSS + class hooks; run StudentSummaryPanel.test + App.studentResume; commit**

```bash
git commit -m "style(student): align plan step and summary with shell"
```

---

### Task 6: VERSION + suite gate

**Files:**
- Modify: `VERSION.md`

- [ ] **Step 1: Note Edition 0901_3 student UI polish (Swiss shell, assessment hierarchy, tutor title)**

- [ ] **Step 2: Run**

```bash
cd frontend; npx vitest run
```

Record counts; pytest unchanged expected (frontend-only) — optional `pytest -q` smoke not required if no Python edits.

- [ ] **Step 3: Commit VERSION**

```bash
git commit -m "docs: note Edition 0901_3 student UI polish"
```

---

## Spec coverage

| Spec item | Task |
| --- | --- |
| student-shell / chrome / steps | 1 |
| 建档 polish | 2 |
| Assessment phase/counter/stem/choices/dots | 3 |
| Tutor 苏格拉底助教 | 4 |
| Plan / summary align | 5 |
| VERSION | 6 |
| Out of scope (Landing/API) | Not tasked |
