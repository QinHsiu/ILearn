# edition_0813 P0+P1 Design

**Date:** 2026-08-13  
**Status:** Approved (approach A — incremental on existing Agent pipeline)  
**Source:** `doc/edition_0813.txt`

## Goal

Ship P0 (UI themes + nickname persistence; paper citations + report traceability) and P1 (four-dimension validators; situational interest dual-track + minimal learning-difficulty path) by extending existing ILearn schemas, orchestrator, Streamlit, and tests — no parallel plugin package.

## Non-goals (P2/P3)

- WCAG three-layer prompts / accessibility Eval protocol
- ParetoGrad / Tutor pedagogical KB training
- Full PyraMathBench corpus / Math-Verify dependency
- New teacher HTTP `approve` surface (draft/superseded already exist)

## Architecture

All changes hang off current types and agents:

- `StudentProfile` / `SessionStore` for identity + theme inputs
- `AssessmentItem` / Assessment + Curriculum flow for `source_refs` + example bank
- Orchestrator post-assessment quality path for validators (generate → validate → one revise)
- `LearnerPortrait` / diagnosis + blueprint fill for interest bias
- Streamlit for theme CSS packs and wrong-item citation expanders

## P0-a — Profile + six themes

**Schema** (`ilearn/core/schemas.py`):

- `nickname: str | None = None`
- `gender: Literal["male", "female", "unspecified"] = "unspecified"`

**Band mapping:** grade 1–6 → `primary`, 7–9 → `junior`, 10–12 → `senior`.  
**Theme key:** `{gender}_{band}` with fallback `unspecified_{band}` (six packs; unspecified counts as the third gender axis → 3 bands × 2 gendered + 3 neutral = 9 files acceptable, or exactly 6 as gender×band with unspecified→neutral CSS).

**Approved mapping (6 packs):**

| Key | Visual |
|-----|--------|
| `primary_playful` | 小学：大圆角、高饱和、卡通图标感 |
| `junior_flat` | 初中：扁平、中密度 |
| `senior_calm` | 高中：低饱和、高密度 |
| Plus gender accent variants: `*_male` / `*_female` OR gender only tweaks accent hue on the three band bases |

**Simplification locked for MVP:** 3 band base themes × gender accent override (male/female/unspecified) implemented as CSS variables files under `ilearn/web/themes/`, selected as `{band}_{gender}.css` → **9 files**; product copy may still say「六套」as 性别×学段主组合（unspecified 用中性）。Streamlit loads selected file after `st.set_page_config`.

**Persistence:** write through existing `SessionState.profile` into `data/sessions/{session_id}.json`. No nickname secondary index required for MVP (optional later).

## P0-b — Citations / example bank

**Schema:**

```python
class ItemSourceRef(BaseModel):
    example_id: str | None = None
    curriculum_objective_ids: list[str] = []
    textbook_chapter: str | None = None
    source_label: str | None = None

# on AssessmentItem
source_refs: list[ItemSourceRef] = []
# keep curriculum_objective_ids for back-compat
```

**Data:** `data/pilot/example_bank.json` — keyed by knowledge_id; ≥1 example per pilot knowledge used in templates (target 3 where easy).

**Binding:** AssessmentAgent / `bind_citations_to_item` also attach `source_refs` from example bank + curriculum citations.

**Report + UI:** `ilearn/core/report.py` wrong-item section; Streamlit diagnosis expanders show 参考来源.

## P1-a — Four validators

**Module:** `ilearn/core/item_validators.py` (pure functions; no new Agent class required unless orchestration clarity wants thin wrappers).

Dimensions:

1. Solvability — answer_key present / parseable for fill/choice; constructed has rubric_steps
2. Realism — numbers in stem not absurd vs grade heuristics
3. Readability — stem length / grade band limits
4. Authenticity — requires `situation_tag` or life-context keyword hit (soft)

**Flow:** after AssessmentAgent paper build, run validators; failed items regenerated once from templates; then existing quality gate.

## P1-b — Interest track + learning_difficulty

**Tags:** `situation_tag: Literal["sports","games","life","science","neutral"] | None` on `ItemTemplate` / `AssessmentItem`.

**Portrait:** extend `PortraitDimensions` or add `LearnerPortrait.situation_interest: dict[str, float]`.

**Signals (MVP):** when grading payload includes optional `skipped` / `elapsed_ms` per item (default missing → no update); diagnose updates preference; follow-up / weak-id fill prefers matching tags.

**learning_difficulty:** optional `bool | None` on profile; when true, consolidate loop max rounds 2→4 and prefer easier blueprint slots (minimal simplified path).

## Testing / acceptance

- New/extended pytest for schema, theme selector, source_refs binding, validators, interest update, learning_difficulty loop cap
- Full `pytest` green
- Streamlit: pick nickname/gender/grade → theme changes; after diagnose, wrong item shows sources

## Risks

- Theme “六套” vs 9 CSS files — document as band×gender including neutral
- Validators are heuristic, not LLM — label as rule-based MVP in VERSION.md
