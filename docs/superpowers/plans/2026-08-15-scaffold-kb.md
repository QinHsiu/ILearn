# Scaffold Pedagogical KB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich offline Socratic hints via PedagogicalKnowledgeBase + JSON strategies, wired only through existing `hint_for_error`, without changing TutorPhase/API/Guard.

**Architecture:** New `pedagogical_kb.py` loads builtin phrases and optional `data/pedagogical_strategies.json`. `hint_for_error` prefers KB text, falls back to `_TAG_HINTS`, keeps streak≥3 escalation. TutorAgent/Guard untouched.

**Tech Stack:** Python 3.11+, pytest, stdlib json.

**Spec:** `docs/superpowers/specs/2026-08-15-scaffold-kb-design.md`

## Global Constraints

- Do **not** change `TutorAgent`, Guard, tutor HTTP APIs, or `TutorTurn` shape.
- Do **not** add ScaffoldState FSM, LLM tutoring, or affective modules.
- Keep `hint_for_error(error_tag, fail_streak=0) -> tuple[HintLevel, str]` signature.
- KB phrases must be plain Chinese (no `{format}` placeholders).
- Offline tests; existing hint/tutor tests stay green.
- Commit on feature branch during SDD.

---

## File map

| File | Responsibility |
| --- | --- |
| `ilearn/core/pedagogical_kb.py` | KB load + retrieve |
| `data/pedagogical_strategies.json` | Overridable phrase bank |
| `ilearn/core/hints.py` | Wire KB into `hint_for_error` |
| `tests/test_pedagogical_kb.py` | KB unit tests |
| `tests/test_practice_hints.py` | Extend or assert KB-backed hints |

---

### Task 1: PedagogicalKnowledgeBase + JSON

**Files:**
- Create: `ilearn/core/pedagogical_kb.py`
- Create: `data/pedagogical_strategies.json`
- Create: `tests/test_pedagogical_kb.py`

**Interfaces:**
- `class PedagogicalKnowledgeBase`
- `retrieve(error_tag: str | None, fail_streak: int = 0) -> str | None`
- `default_kb() -> PedagogicalKnowledgeBase` (lazy singleton for hints.py)

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from ilearn.core.pedagogical_kb import PedagogicalKnowledgeBase


def test_retrieve_concept_gap_returns_chinese():
    kb = PedagogicalKnowledgeBase(data_path=None)  # builtin only
    text = kb.retrieve("concept_gap", fail_streak=0)
    assert text
    assert "答案" not in text  # no answer leak phrases


def test_retrieve_escalates_index_with_streak():
    kb = PedagogicalKnowledgeBase(data_path=None)
    a = kb.retrieve("calc_error", 0)
    b = kb.retrieve("calc_error", 1)
    # If multiple phrases exist, streak may pick later; if only one, same string OK
    assert a and b


def test_missing_json_uses_builtin(tmp_path: Path):
    kb = PedagogicalKnowledgeBase(data_path=tmp_path / "missing.json")
    assert kb.retrieve("misread", 0)


def test_json_override(tmp_path: Path):
    path = tmp_path / "pedagogical_strategies.json"
    path.write_text(
        '{"conceptual":{"default":["自定义概念提示"]}}',
        encoding="utf-8",
    )
    kb = PedagogicalKnowledgeBase(data_path=path)
    assert kb.retrieve("concept_gap", 0) == "自定义概念提示"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_pedagogical_kb.py -v
```

- [ ] **Step 3: Implement KB + JSON**

`ilearn/core/pedagogical_kb.py` outline:

```python
from __future__ import annotations

import json
from pathlib import Path

_ERROR_TAG_BUCKET = {
    "concept_gap": "conceptual",
    "calc_error": "procedural",
    "incomplete": "procedural",
    "method_wrong": "procedural",
    "misread": "metacognitive",
}

_BUILTIN = {
    "conceptual": {
        "default": [
            "回顾相关定义：这个概念的关键条件是什么？",
            "能不能用自己的话再说一遍这道题在问什么？",
        ]
    },
    "procedural": {
        "default": [
            "检查运算步骤：相同数位是否对齐？有没有漏步骤？",
            "换一种列式思路：先写已知，再求未知。",
        ]
    },
    "metacognitive": {
        "default": [
            "再读一遍题目，圈出所有已知条件和所求。",
            "如果现在自查，你最想先检查哪一步？",
        ]
    },
}


def _default_data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "pedagogical_strategies.json"


class PedagogicalKnowledgeBase:
    def __init__(self, data_path: str | Path | None = ...) -> None:
        # If data_path is the sentinel ..., use _default_data_path().
        # If data_path is None, builtin only (no file load).
        ...

    def retrieve(self, error_tag: str | None, fail_streak: int = 0) -> str | None:
        bucket = _ERROR_TAG_BUCKET.get(error_tag or "", "metacognitive")
        phrases = list(self.strategies.get(bucket, {}).get("default", []))
        if not phrases:
            return None
        idx = min(max(fail_streak, 0), len(phrases) - 1)
        return phrases[idx]


_kb: PedagogicalKnowledgeBase | None = None

def default_kb() -> PedagogicalKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = PedagogicalKnowledgeBase()
    return _kb
```

Create `data/pedagogical_strategies.json` mirroring `_BUILTIN` (can add 1–2 extra phrases per bucket).

- [ ] **Step 4: PASS + commit**

```bash
python -m pytest tests/test_pedagogical_kb.py -v
git add ilearn/core/pedagogical_kb.py data/pedagogical_strategies.json tests/test_pedagogical_kb.py
git commit -m "feat: add pedagogical knowledge base for offline hints"
```

---

### Task 2: Wire `hint_for_error`

**Files:**
- Modify: `ilearn/core/hints.py`
- Modify or extend: `tests/test_practice_hints.py` (read existing tests first and adapt)

**Interfaces:**
- Same `hint_for_error` signature; uses `default_kb().retrieve`

- [ ] **Step 1: Add/adjust failing tests** proving KB text is used for `concept_gap` when builtin/JSON provides distinct phrase from old `_TAG_HINTS` short string — OR assert that returned text equals `PedagogicalKnowledgeBase(data_path=None).retrieve("concept_gap", 0)` when that is not None.

Also keep streak≥3 suffix test from existing suite.

- [ ] **Step 2: Run FAIL if wiring absent**

- [ ] **Step 3: Update `hints.py`**

```python
from ilearn.core.pedagogical_kb import default_kb

def hint_for_error(error_tag: str | None, fail_streak: int = 0) -> tuple[HintLevel, str]:
    level, text = _TAG_HINTS.get(error_tag or "", _DEFAULT_HINT)
    kb_text = default_kb().retrieve(error_tag, fail_streak)
    if kb_text:
        text = kb_text
    if fail_streak >= _STREAK_ESCALATION_THRESHOLD:
        level = "high"
        if _STREAK_ESCALATION_SUFFIX not in text:
            text = f"{text}；{_STREAK_ESCALATION_SUFFIX}"
    return level, text
```

- [ ] **Step 4: Run hint + tutor related tests**

```bash
python -m pytest tests/test_pedagogical_kb.py tests/test_practice_hints.py tests/test_hint_interactions.py tests/test_tutor_agent.py -v
```

(Skip missing test files; run what exists.)

- [ ] **Step 5: Commit**

```bash
git add ilearn/core/hints.py tests/
git commit -m "feat: prefer pedagogical KB text in hint_for_error"
```

---

### Task 3: Verification gate

```bash
python -m pytest tests/test_pedagogical_kb.py tests/test_practice_hints.py -v
python -m pytest -q
git diff --stat master...HEAD
```

Expected: only KB + JSON + hints.py + tests; no tutor.py / API / frontend.

---

## Self-review

| Spec | Task |
| --- | --- |
| pedagogical_kb + JSON | Task 1 |
| hint_for_error wiring | Task 2 |
| No TutorAgent/Guard/LLM/ScaffoldState | Global + Task 3 |
