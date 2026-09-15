# Diagnostic Rules / SOLO Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rule/SOLO enrichment that appends explainable `flags` and lightly enriches intervention `why` text inside existing `Diagnoser.diagnose`, without changing mastery math or API contracts.

**Architecture:** New pure module `ilearn/core/diagnostic_rules.py` (adapted from `0815_e2` rules/SOLO essence). `Diagnoser.diagnose` calls `enrich_diagnosis` after building interventions and gap flags, then merges flags and suffixes `why`. No DINA/LLM/Q-matrix port.

**Tech Stack:** Python 3.11+, existing Pydantic schemas, pytest.

**Spec:** `docs/superpowers/specs/2026-08-15-diagnostic-enrichment-design.md`

## Global Constraints

- Do **not** change `DiagnosisReport` fields, mastery/`_build_interventions` selection order, or `Diagnoser.diagnose` / `DiagnosisAgent` signatures.
- Do **not** port DINA, async `diagnose_question`, hardcoded Q-matrix, or SmartLLM wiring.
- Grades-only SOLO this slice (no answers parameter on Diagnoser).
- Flag prefixes: `solo:<level>`, `rule:<error_tag>` (max 5 rule flags).
- Offline tests; existing diagnosis tests must stay green.
- Commit on feature branch during SDD.

---

## File map

| File | Responsibility |
| --- | --- |
| `ilearn/core/diagnostic_rules.py` | ErrorType mapping, SOLO, `enrich_diagnosis` |
| `ilearn/core/diagnosis.py` | Hook merge flags + why suffixes |
| `tests/test_diagnostic_rules.py` | Unit tests for rules module |
| `tests/test_diagnosis_enrichment.py` | Diagnoser integration: `solo:` in flags |

---

### Task 1: `diagnostic_rules` module (TDD)

**Files:**
- Create: `ilearn/core/diagnostic_rules.py`
- Create: `tests/test_diagnostic_rules.py`

**Interfaces:**
- Produces:
  - `ErrorType` enum
  - `ERROR_TAG_TO_TYPE: dict[str, ErrorType]`
  - `SOLO_LEVEL_KEYS` / `classify_solo_from_grades(grades: list[GradeResult]) -> str` returning one of `prestructural|unistructural|multistructural|relational`
  - `@dataclass Enrichment: flags: list[str]; why_suffix_by_knowledge_id: dict[str, str]`
  - `enrich_diagnosis(*, knowledge_mastery: list[KnowledgeMastery], grades: list[GradeResult]) -> Enrichment`

- [ ] **Step 1: Write failing tests**

```python
from ilearn.core.diagnostic_rules import (
    ERROR_TAG_TO_TYPE,
    ErrorType,
    classify_solo_from_grades,
    enrich_diagnosis,
)
from ilearn.core.schemas import GradeResult, KnowledgeMastery


def test_error_tag_mapping():
    assert ERROR_TAG_TO_TYPE["concept_gap"] == ErrorType.CONCEPTUAL
    assert ERROR_TAG_TO_TYPE["calc_error"] == ErrorType.PROCEDURAL
    assert ERROR_TAG_TO_TYPE["misread"] == ErrorType.READING
    assert ERROR_TAG_TO_TYPE["method_wrong"] == ErrorType.TRANSFER
    assert ERROR_TAG_TO_TYPE["incomplete"] == ErrorType.PROCEDURAL


def test_solo_prestructural_when_all_wrong_empty_tags():
    grades = [
        GradeResult(item_id="q1", final_correct=False, error_tags=[]),
        GradeResult(item_id="q2", final_correct=False, error_tags=[]),
    ]
    assert classify_solo_from_grades(grades) == "prestructural"


def test_solo_unistructural_when_wrong_with_tags():
    grades = [
        GradeResult(item_id="q1", final_correct=False, error_tags=["concept_gap"]),
    ]
    assert classify_solo_from_grades(grades) == "unistructural"


def test_solo_multistructural_when_mostly_correct():
    grades = [
        GradeResult(item_id="q1", final_correct=True, error_tags=[]),
        GradeResult(item_id="q2", final_correct=True, error_tags=[]),
        GradeResult(item_id="q3", final_correct=False, error_tags=["calc_error"]),
    ]
    assert classify_solo_from_grades(grades) == "multistructural"


def test_enrich_diagnosis_flags_and_suffix():
    grades = [
        GradeResult(
            item_id="q1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["k1"],
        ),
    ]
    mastery = [
        KnowledgeMastery(
            knowledge_id="k1",
            score_rate=0.0,
            error_tag_counts={"concept_gap": 1},
            level="weak",
            item_ids=["q1"],
        )
    ]
    enrichment = enrich_diagnosis(knowledge_mastery=mastery, grades=grades)
    assert "solo:unistructural" in enrichment.flags
    assert "rule:concept_gap" in enrichment.flags
    assert "k1" in enrichment.why_suffix_by_knowledge_id
    assert enrichment.why_suffix_by_knowledge_id["k1"]


def test_enrich_empty_grades():
    enrichment = enrich_diagnosis(knowledge_mastery=[], grades=[])
    assert enrichment.flags == []
    assert enrichment.why_suffix_by_knowledge_id == {}
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_diagnostic_rules.py -v
```

- [ ] **Step 3: Implement `diagnostic_rules.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ilearn.core.schemas import GradeResult, KnowledgeMastery

# Chinese short labels for why suffixes
_ERROR_TAG_ZH = {
    "concept_gap": "概念缺口",
    "calc_error": "计算错误",
    "misread": "审题失误",
    "method_wrong": "方法不当",
    "incomplete": "步骤不完整",
}

_SOLO_ZH = {
    "prestructural": "SOLO前结构",
    "unistructural": "SOLO单点结构",
    "multistructural": "SOLO多点结构",
    "relational": "SOLO关联结构",
}


class ErrorType(Enum):
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    CARELESS = "careless"
    TRANSFER = "transfer"
    READING = "reading"


ERROR_TAG_TO_TYPE: dict[str, ErrorType] = {
    "concept_gap": ErrorType.CONCEPTUAL,
    "calc_error": ErrorType.PROCEDURAL,
    "misread": ErrorType.READING,
    "method_wrong": ErrorType.TRANSFER,
    "incomplete": ErrorType.PROCEDURAL,
}


@dataclass
class Enrichment:
    flags: list[str] = field(default_factory=list)
    why_suffix_by_knowledge_id: dict[str, str] = field(default_factory=dict)


def classify_solo_from_grades(grades: list[GradeResult]) -> str:
    if not grades:
        return "prestructural"
    correct = sum(1 for g in grades if g.final_correct)
    incorrect = len(grades) - correct
    any_tags = any(g.error_tags for g in grades)
    if incorrect == len(grades) and not any_tags:
        return "prestructural"
    if incorrect == len(grades) and any_tags:
        return "unistructural"
    if correct == len(grades) and len(grades) >= 2:
        return "relational"
    if correct > incorrect:
        return "multistructural"
    if any_tags:
        return "unistructural"
    return "prestructural"


def enrich_diagnosis(
    *,
    knowledge_mastery: list[KnowledgeMastery],
    grades: list[GradeResult],
) -> Enrichment:
    if not grades:
        return Enrichment()

    solo = classify_solo_from_grades(grades)
    flags: list[str] = [f"solo:{solo}"]

    seen_tags: list[str] = []
    for g in grades:
        for tag in g.error_tags:
            if tag in ERROR_TAG_TO_TYPE and tag not in seen_tags:
                seen_tags.append(tag)
    for tag in seen_tags[:5]:
        flags.append(f"rule:{tag}")

    suffixes: dict[str, str] = {}
    solo_zh = _SOLO_ZH.get(solo, f"SOLO{solo}")
    for km in knowledge_mastery:
        if km.level == "mastered":
            continue
        dominant = None
        if km.error_tag_counts:
            dominant = max(km.error_tag_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        parts = [solo_zh]
        if dominant and dominant in _ERROR_TAG_ZH:
            parts.append(f"规则偏向{_ERROR_TAG_ZH[dominant]}")
        suffixes[km.knowledge_id] = "；".join(parts)

    return Enrichment(flags=flags, why_suffix_by_knowledge_id=suffixes)
```

Tune `classify_solo_from_grades` if a test expectation conflicts — prefer making heuristics match the tests above.

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_diagnostic_rules.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/diagnostic_rules.py tests/test_diagnostic_rules.py
git commit -m "feat: add diagnostic rules and SOLO enrichment helpers"
```

---

### Task 2: Hook into `Diagnoser.diagnose`

**Files:**
- Modify: `ilearn/core/diagnosis.py` (diagnose return path ~195–212)
- Create: `tests/test_diagnosis_enrichment.py`

**Interfaces:**
- Consumes: `enrich_diagnosis`
- Produces: richer `DiagnosisReport.flags` and intervention `why` strings

- [ ] **Step 1: Write failing Diagnoser integration test**

```python
from pathlib import Path

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_diagnoser_adds_solo_and_rule_flags():
    diagnoser = Diagnoser(PilotBeijingRenjiaoProvider(PILOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    paper = AssessmentPaper(
        curriculum_label="pilot",
        grade=5,
        items=[
            AssessmentItem(
                id="q1",
                stem="1",
                answer_key="1",
                knowledge_ids=["frac_add_same"],
                item_type="fill",
            )
        ],
    )
    grades = [
        GradeResult(
            item_id="q1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
        )
    ]
    report = diagnoser.diagnose(profile, paper, grades)
    assert any(f.startswith("solo:") for f in report.flags)
    assert "rule:concept_gap" in report.flags
    assert report.interventions
    assert "SOLO" in report.interventions[0].why or "规则" in report.interventions[0].why
```

Adjust `AssessmentItem` / `AssessmentPaper` required fields to match existing schema used in `tests/test_agents_diagnosis.py` (copy that fixture style if this sketch fails to construct).

- [ ] **Step 2: Run — expect FAIL** (no solo flags yet)

```bash
python -m pytest tests/test_diagnosis_enrichment.py -v
```

- [ ] **Step 3: Hook Diagnoser**

In `diagnose`, after `flags = gap_flag(effective_portrait)` and before building `DiagnosisReport`:

```python
from ilearn.core.diagnostic_rules import enrich_diagnosis

        enrichment = enrich_diagnosis(
            knowledge_mastery=knowledge_mastery,
            grades=grades,
        )
        flags = list(dict.fromkeys([*flags, *enrichment.flags]))
        if enrichment.why_suffix_by_knowledge_id:
            for intervention in interventions:
                suffix = enrichment.why_suffix_by_knowledge_id.get(
                    intervention.knowledge_id  # verify Intervention field name
                )
                if suffix:
                    intervention.why = f"{intervention.why}；{suffix}"
```

Check `Intervention` schema for the knowledge id field name (`knowledge_id` vs embedded in `what_to_fix_first`). Read `schemas.py` `Intervention` and use the correct attribute; if Intervention has no `knowledge_id`, match via intervention order to non-mastered mastery list or add suffix using the same candidates loop — **prefer reading Intervention fields and attaching by the field that identifies the KC**.

If `Intervention` lacks `knowledge_id`, enrich inside `_build_interventions` is forbidden by plan (don't change selection). Alternative: rebuild interventions list with updated why by zipping Top-5 candidates knowledge ids:

```python
weak_ids = [
    km.knowledge_id
    for km in sorted(...)
]  # DO NOT re-sort — instead:
for intervention, km in zip(
    interventions,
    [km for km in knowledge_mastery if km.level != "mastered"][:5],
    strict=False,
):
```

Simplest correct approach: read Intervention model; if it has `knowledge_id`, use it. If not, store suffixes only applied by iterating `interventions` with parallel list of knowledge ids collected during `_build_interventions` — **minimal change**: add optional return of ordered knowledge ids from a small helper, OR set `intervention.why` by parsing — bad.

**Required check before coding:** open `Intervention` in `schemas.py`. If no `knowledge_id`, extend Enrichment application by modifying `_build_interventions` **only** to accept optional `why_suffixes` dict and append when building each intervention (still same selection). That is allowed as it does not change selection order — update this task to pass `why_suffixes` into `_build_interventions` if needed.

Preferred if `Intervention` has no knowledge_id:

1. Call `enrich_diagnosis` **before** `_build_interventions`.
2. Pass `why_suffixes=enrichment.why_suffix_by_knowledge_id` into `_build_interventions`.
3. When setting `why`, append suffix.
4. Merge flags after as planned.

- [ ] **Step 4: Run enrichment + rules + agents diagnosis tests**

```bash
python -m pytest tests/test_diagnostic_rules.py tests/test_diagnosis_enrichment.py tests/test_agents_diagnosis.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/diagnosis.py tests/test_diagnosis_enrichment.py
git commit -m "feat: enrich Diagnoser flags and intervention why via SOLO/rules"
```

---

### Task 3: Verification gate

- [ ] **Step 1:**

```bash
python -m pytest tests/test_diagnostic_rules.py tests/test_diagnosis_enrichment.py tests/test_agents_diagnosis.py tests/test_session_store.py -v
python -m pytest -q
```

- [ ] **Step 2:** Diff vs master only touches `diagnostic_rules.py`, `diagnosis.py`, and the two new test files (plus any tiny Intervention-related hook). No frontend/API/DINA.

- [ ] **Step 3:** Mark slice complete; do not start scaffold unless asked.

---

## Self-review

| Spec | Task |
| --- | --- |
| diagnostic_rules mapping + SOLO + enrich | Task 1 |
| Diagnoser flags + why | Task 2 |
| No schema/API/DINA/LLM | Global + Task 3 |
| Existing tests green | Task 2–3 |
