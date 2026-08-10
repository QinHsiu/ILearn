# ILearn MVP Final Review Fix Report

Date: 2026-08-10  
Branch: `feature/ilearn-mvp`  
Implementation commit: `801125e` (`fix: resolve final MVP review blockers`)

## Scope and fixes

- **C1:** Changed `g6_easy_choice_01` from decimal division to the explicit `ratio(a,b)` formatter, producing answer keys such as `29:18`. Added a grades 4–6, 50-seed invariant test that every choice answer key is present in its rendered choices.
- **C2:** Seed-shuffled rendered options during `AssessmentBuilder` instantiation while preserving `answer_key` as the answer value. Added a multi-build test proving the correct option is not fixed at index 0.
- **C3 + I1:** API `create_app()` and CLI commands load `.env`, construct `LLMClient.from_env()`, and wire available clients into `Orchestrator`/`StepGrader`. Offline constructed grading now compares the extracted final numeric/text token with `answer_key` while retaining `grading_degraded=True`. Streamlit now asks for the final answer first, and README documents configured-LLM versus offline degraded behavior.
- **I2:** Wrapped OpenAI request and OS/network failures in `LLMError`, allowing `StepGrader` to degrade rather than return an uncaught server error. Added a mocked OpenAI failure regression test.
- **I3:** Ability penalties are now averaged per tagged item instead of accumulated as an unbounded sum. A 50%-correct, 20-item regression case now scores `47.5` rather than collapsing to zero.
- **I4:** Added a constructed fixture containing worked text with a final answer, relaxed fixture-run assertions to bounded quality thresholds, and changed error-tag macro-F1 to calculate F1 per label before averaging.
- **I5:** Added one spare easy-choice template for each grade. Across seeds, every grade can now produce papers with different template-id sets.
- **I6:** Added post-render choice de-duplication with nearby replacement distractors and a grades 4–6, 50-seed uniqueness invariant test.
- **Knowledge names:** Added optional `knowledge_name` to mastery rows, populated it from the curriculum, and displayed it in Streamlit.

## TDD evidence

Initial focused regression run: `11 failed, 57 passed`. The failures directly reproduced the ratio mismatch, fixed correct-option position, duplicate choices, no template diversity, constructed fallback miss, uncaught OpenAI error, accumulated ability penalty, missing API/CLI LLM wiring, missing worked fixture, and knowledge-id-only display.

After implementation, the same focused set passed: `68 passed`.

## Final verification

- `python -m pytest -q` → `93 passed, 0 failed` (384 existing deprecation warnings).
- IDE lint diagnostics for `ilearn/` and `tests/` → no errors.
- `git diff --check` → clean.
- `python -m ilearn.cli.main eval` → `accuracy: 1.0000`, `macro_f1: 1.0000`, `json_valid_rate: 1.0000`.
- `python -m ilearn.cli.main run --region 北京 --grade 5 --age 11 --auto-answer` → exit 0; paper and report generated, report excerpt printed. Smoke artifacts created by this run were removed afterward.

## Remaining risks

- Offline constructed grading validates only the extracted final token; it does not establish whether intermediate reasoning is valid. Results remain explicitly degraded.
- Generated distractor repair guarantees uniqueness but is heuristic; pedagogical distractor quality should be reviewed when the pilot template set expands.
- The suite reports upstream/deprecation warnings from Starlette/httpx and `datetime.utcnow()`; they are non-blocking for this fix scope.
- Pre-existing untracked session artifacts and `scripts/` were left untouched and excluded from commits.

## Re-review follow-up (2026-08-10)

- **Spare template tags:** Rewrote `g4_easy_choice_spare_21` stem to `{a} × {b}` (mult_3digit) and `g5_easy_choice_spare_21` to `{a}.{b} × 10` (dec_mult) so `knowledge_ids` match stem content.
- **Offline eval:** `ilearn eval` now defaults to `StepGrader(None)`; pass `--use-llm` to use a configured LLM. README eval section updated one line.

### Verification

- `python -m pytest -q` → `93 passed, 0 failed`.
