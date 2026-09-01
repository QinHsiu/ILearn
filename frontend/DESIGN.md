# ILearn Landing Page Design System

**Status:** Approved direction, pending implementation review
**Source templates:** HTML Anything `deck-swiss-international`, `dashboard`, `article-magazine`

## 1. Design intent

ILearn is an evidence-led learning guide. The first screen should feel calm,
precise, and purposeful rather than like a generic admin login. The visual
language combines Swiss Internationalist structure with editorial education
content: strict grid, strong typography, one saturated accent, and concise
explanations.

## 2. Color tokens

```css
--il-blue: #002FA7;
--il-paper: #FAFAF8;
--il-ink: #0A0A0A;
--il-muted: #5F6368;
--il-line: #C9CCD2;
--il-soft: #EEF1F7;
--il-danger: #B42318;
```

Use `--il-blue` for primary actions, active markers, and role index blocks.
Use black text on paper backgrounds. Do not introduce gradients, blur, or
decorative color combinations.

## 3. Typography

- Brand / Latin wordmark: `Instrument Serif` (italic), fallback Times New Roman.
- Display (Chinese headlines / role titles): `LXGW WenKai` (霞鹜文楷), fallback
  Songti SC / serif. Prefer weight 400 — heavy weights flatten the kai texture.
- Body: `Noto Sans SC` 300–500, fallback Microsoft YaHei.
- Data labels: `JetBrains Mono`.
- Chinese display tracking: ~0.06–0.08em; line-height ~1.3–1.35.
- Body tracking: ~0.03–0.04em; line-height ~1.8 on marketing lede.
- Load `Instrument Serif` + `Noto Sans SC` + Mono from Google Fonts; load
  LXGW WenKai from jsDelivr webfont CSS.

## 4. Layout

- Main landing shell: max-width 1280px, centered (`margin: 0 auto`), 12-column grid.
- Desktop gutters: ~24px; mobile gutters: ~14–16px.
- Header: brand block left, edition meta right-aligned.
- Hero uses columns 1–6 for the statement; role entry rail uses columns 7–12
  (equal visual weight; avoid a skinny right rail that reads as empty space).
- Workflow strip spans all columns and uses three equal cells.
- Dashboard pages reuse the same paper, ink, blue, line, and square geometry.

## 5. Role-specific product surfaces

The three roles share the ILearn visual system but do not share the same
information hierarchy or primary action.

### Parent surface: growth companion

- Primary question: “孩子最近学得怎么样，下一步怎么支持？”
- Header: `家长端 / CHILD GROWTH` with a calm blue accent and selected-child
  context.
- First content row: child selector and three factual summary cards:
  current mastery, weak skills, and learning phase.
- Main content: selected child detail with diagnosis, plan status, and
  actionable support suggestions.
- Primary action: select a child or bind a learning session.
- Avoid teacher language such as “班级管理”, rankings, or operational tables.

### Teacher surface: class operations

- Primary question: “班级整体哪里需要干预，应该先看谁？”
- Header: `老师端 / CLASS STUDIO` with a stronger blue index marker and class
  context.
- First content row: class selector and class-level student count/status.
- Main content: student list optimized for scanning, with mastery, weak-skill,
  and phase metadata; selected student detail appears beside or below it.
- Primary action: select a class, inspect a student, or bind a student session.
- Avoid parent-style emotional copy or child-only onboarding instructions.

### Student surface: next learning action

- Primary question: “我现在要做什么，怎样变得更好？”
- Header: `学生学习 / NEXT STEP` with a more welcoming but still structured
  treatment.
- First content row: profile setup or current assessment progress.
- Main content: assessment, Socratic help, diagnosis, and learning plan in the
  existing step order.
- Primary action: start assessment, answer, request a hint, or follow the plan.
- Keep teacher/parent identifiers and relationship controls out of the student
  experience.

### Shared rules

- Each surface has one clear primary action and no competing role controls.
- Role labels are explicit text, not color-only signals.
- Reuse tokens, grid, focus states, and square geometry, but allow role-specific
  density: parent is summary-oriented, teacher is scan-oriented, student is
  action-oriented.
- Data shown must come from existing ILearn session metadata, diagnosis, plan,
  and relationship APIs. Do not invent trends or metrics.

## 6. Role entry components

Each role entry is a square-corner card with:

- A blue numbered marker: `01` 家长, `02` 老师, `03` 学生.
- A short role title.
- One-line purpose statement.
- A right-aligned arrow or `↗`.
- A thin black or blue border; no shadow.

Cards must be keyboard-focusable and expose a clear accessible name. Hover
changes the background to `--il-blue`, changes text to white, and preserves
the border contrast. Reduced-motion users receive no transform animation.

## 7. Workflow strip

Show three factual steps only:

1. 诊断 — 识别知识点掌握情况
2. 计划 — 生成下一步学习路径
3. 反馈 — 根据练习结果持续调整

Use a hairline separator and compact mono labels. Do not add fabricated
statistics, testimonials, or historical performance claims.

## 8. Login and navigation

- Role cards link to the existing `?login=1&role=...` routes.
- Student card links to `?student=1`.
- Login page uses the same grid and square controls.
- Dashboard back navigation returns to `/`.
- Existing role/user query contracts remain unchanged.

## 9. Motion and interaction

- Use only short opacity/color transitions up to 180ms.
- No parallax, bounce, blur, or continuous animation.
- Focus state: 2px solid `--il-blue` with 2px offset.
- Respect `prefers-reduced-motion: reduce`.

## 10. Responsive behavior

- At widths below 900px, hero becomes one column and the role rail moves below
  the headline.
- At widths below 640px, use a single-column card stack, 20px gutters, and a
  3rem minimum headline size.
- No horizontal scrolling.
- Preserve minimum 44px interactive target height.

## 11. Accessibility and content rules

- Maintain semantic heading order and visible labels.
- Never communicate role meaning by color alone.
- Keep Chinese copy concise and action-oriented.
- Do not expose passwords, credentials, or internal IDs in the visual UI.
- Keep current API error text visible in an `aria-live` error region.
