# Edition 0909_1 Enhanced Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 旁路合入 edition_0909_1（A+C）：三 PR、Feature Flag 默认关闭、旧链路不变。

**Architecture:** 新代码落在 `ilearn/core/models`、`ilearn/agents/enhanced`、dashboard 查询分支；五维画像存 `metadata.enhanced`；flags 读 `data/features.yaml` + `ILEARN_*` 环境覆盖。

**Tech Stack:** Python 3.11+, Pydantic, FastAPI, pytest, 现有 `SessionStore` / `LLMClient`

## Global Constraints

- Path rewrite: `app/` → `ilearn/`; never overwrite existing files.
- No SQL migrations; persist under `SessionState.metadata["enhanced"]`.
- LLM only via `ilearn.providers.llm` / existing free_llm fallback.
- Flags default `false`; AGENTS/API no-op if PROFILE flag false.
- Do not change default orchestrator outputs when flags are off.
- Source draft: `doc/edition_0909_1.txt`; design: `docs/superpowers/specs/2026-09-09-edition-0909-1-enhanced-merge-design.md`.

---

## File Structure (all PRs)

| File | Responsibility | PR |
| --- | --- | --- |
| `data/features.yaml` | Flag defaults | #01 |
| `ilearn/core/enhanced_flags.py` | Load YAML + env override | #01 |
| `ilearn/core/models/__init__.py` | Package export | #01 |
| `ilearn/core/models/enhanced_profile.py` | Five-dim models (§1.1) | #01 |
| `ilearn/core/enhanced_profile_adapter.py` | Bidirectional adapter | #01 |
| `ilearn/core/enhanced_session.py` | get/set `metadata.enhanced` | #01 |
| `tests/test_edition_0909_1_pr01.py` | PR#01 acceptance | #01 |
| `ilearn/agents/enhanced/__init__.py` | Package | #02 |
| `ilearn/agents/enhanced/profile_updater.py` | Multi-agent profile update | #02 |
| `ilearn/agents/enhanced/recommendation.py` | Rec engine (offline-safe) | #02 |
| `ilearn/agents/enhanced/question_generator.py` | Item gen (offline-safe) | #02 |
| `ilearn/agents/orchestrator.py` | Conditional hooks only | #02 |
| `tests/test_edition_0909_1_pr02.py` | Flag off parity + on path | #02 |
| `ilearn/api/dashboard.py` | `?enhanced=` branches | #03 |
| `ilearn/api/enhanced_report.py` | Gated PDF route | #03 |
| `ilearn/api/app.py` | Mount enhanced router | #03 |
| `tests/test_edition_0909_1_pr03.py` | API default/enhanced | #03 |

---

### Task 1: Feature flags (PR #01)

**Files:**
- Create: `data/features.yaml`
- Create: `ilearn/core/enhanced_flags.py`
- Test: `tests/test_edition_0909_1_pr01.py`

**Interfaces:**
- Produces: `is_enhanced_enabled(name: str) -> bool` where `name` in `ENABLE_ENHANCED_PROFILE|AGENTS|API`
- Env: `ILEARN_ENABLE_ENHANCED_PROFILE=1` overrides YAML

- [x] **Step 1: Write failing tests for flags**

```python
from ilearn.core.enhanced_flags import is_enhanced_enabled

def test_flags_default_false():
    assert is_enhanced_enabled("ENABLE_ENHANCED_PROFILE") is False
    assert is_enhanced_enabled("ENABLE_ENHANCED_AGENTS") is False
    assert is_enhanced_enabled("ENABLE_ENHANCED_API") is False

def test_flag_env_override(monkeypatch):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    assert is_enhanced_enabled("ENABLE_ENHANCED_PROFILE") is True
```

- [x] **Step 2: Run tests — expect fail (module missing)**

Run: `python -m pytest tests/test_edition_0909_1_pr01.py::test_flags_default_false -v`

- [x] **Step 3: Implement `data/features.yaml` + loader**

```yaml
ENABLE_ENHANCED_PROFILE: false
ENABLE_ENHANCED_AGENTS: false
ENABLE_ENHANCED_API: false
```

```python
# ilearn/core/enhanced_flags.py
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path

_KNOWN = (
    "ENABLE_ENHANCED_PROFILE",
    "ENABLE_ENHANCED_AGENTS",
    "ENABLE_ENHANCED_API",
)

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, bool]:
    path = _repo_root() / "data" / "features.yaml"
    if not path.is_file():
        return {k: False for k in _KNOWN}
    try:
        import yaml  # PyYAML if present
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        # minimal fallback parser for key: true/false lines
        data = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            data[k.strip()] = str(v.strip()).lower() in {"1", "true", "yes", "on"}
    return {k: bool(data.get(k, False)) for k in _KNOWN}

def is_enhanced_enabled(name: str) -> bool:
    if name not in _KNOWN:
        return False
    env = os.getenv(f"ILEARN_{name}")
    if env is not None and env.strip() != "":
        return env.strip().lower() in {"1", "true", "yes", "on"}
    return bool(_load_yaml().get(name, False))

def clear_enhanced_flag_cache() -> None:
    _load_yaml.cache_clear()
```

Prefer stdlib-only fallback so PyYAML is not a new hard dep unless already in project.

- [x] **Step 4: Run flag tests — expect PASS**

- [ ] **Step 5: Commit** (only if user asked to commit; otherwise leave staged work)

---

### Task 2: Five-dim model (PR #01)

**Files:**
- Create: `ilearn/core/models/__init__.py`
- Create: `ilearn/core/models/enhanced_profile.py` (port `doc/edition_0909_1.txt` §1.1)
- Modify: `tests/test_edition_0909_1_pr01.py`

**Interfaces:**
- Produces: `StudentFiveDimProfile`, dimension models, `BloomLevel`, `EmotionType`, `LearningStyle`
- Note: local `CognitiveDimension` is a **BaseModel**; do not import alongside Bloom Enum without alias

- [ ] **Step 1: Failing test — construct + round-trip**

```python
from ilearn.core.models.enhanced_profile import StudentFiveDimProfile

def test_five_dim_round_trip():
    p = StudentFiveDimProfile(student_id="s1")
    p.cognitive.knowledge_mastery["kp_a"] = 0.8
    data = p.model_dump(mode="json")
    restored = StudentFiveDimProfile.model_validate(data)
    assert restored.get_mastery_for_concept("kp_a") == 0.8
    assert restored.get_overall_mastery() == 0.8
```

- [ ] **Step 2: Port §1.1 into `enhanced_profile.py`** (typing modernized to `dict|list`, `datetime` via `utc_now` if project prefers)

- [ ] **Step 3: Export from `ilearn/core/models/__init__.py`**

- [ ] **Step 4: pytest PASS**

---

### Task 3: Adapter + session helpers (PR #01)

**Files:**
- Create: `ilearn/core/enhanced_profile_adapter.py`
- Create: `ilearn/core/enhanced_session.py`
- Modify: `tests/test_edition_0909_1_pr01.py`
- Touch only via helpers — **do not** change `SessionStore.save/load` signatures

**Interfaces:**
- `ProfileAdapter.from_session(session: SessionState) -> StudentFiveDimProfile`
- `ProfileAdapter.apply_cognitive_to_legacy_dict(profile) -> dict[str, float]` (for optional consumers; legacy diagnosis untouched)
- `get_enhanced_profile(session) -> StudentFiveDimProfile | None`
- `set_enhanced_profile(session, profile) -> SessionState` mutates `metadata["enhanced"] = {"schema_version": 1, "profile": ...}`
- When `ENABLE_ENHANCED_PROFILE` is false, `set_enhanced_profile` is a no-op (returns session unchanged, does not write key)

- [ ] **Step 1: Failing acceptance tests**

```python
def test_set_enhanced_writes_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("ILEARN_ENABLE_ENHANCED_PROFILE", "1")
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    profile = StudentFiveDimProfile(student_id=session.session_id)
    profile.cognitive.knowledge_mastery["kp_1"] = 0.3
    session = set_enhanced_profile(session, profile)
    store.save(session)
    loaded = store.load(session.session_id)
    blob = loaded.metadata.get("enhanced")
    assert isinstance(blob, dict)
    assert blob["schema_version"] == 1
    assert blob["profile"]["cognitive"]["knowledge_mastery"]["kp_1"] == 0.3

def test_flag_off_set_is_noop(monkeypatch, tmp_path):
    monkeypatch.delenv("ILEARN_ENABLE_ENHANCED_PROFILE", raising=False)
    clear_enhanced_flag_cache()
    store = SessionStore(tmp_path)
    session = store.create(StudentProfile(region="北京", grade=5, age=11))
    session = set_enhanced_profile(session, StudentFiveDimProfile(student_id=session.session_id))
    assert "enhanced" not in session.metadata

def test_legacy_metadata_mastery_unaffected(tmp_path):
    # create session with diagnosis knowledge_mastery; list_all_metadata overall_mastery
    # writing enhanced must not change overall_mastery projection
    ...
```

- [ ] **Step 2: Implement adapter** — map `session.profile` → contextual; map `diagnosis.knowledge_mastery` rows → `cognitive.knowledge_mastery` scores when bootstrapping

- [ ] **Step 3: Implement session helpers**

- [ ] **Step 4: Full PR#01 pytest PASS**

- [ ] **Step 5: Run broader smoke** `python -m pytest tests/test_session_store.py -q` — expect unchanged PASS

---

### Task 4: PR #02 — Enhanced agents package

**Files:**
- Create: `ilearn/agents/enhanced/__init__.py`
- Create: `ilearn/agents/enhanced/profile_updater.py` (port §1.2; replace `get_llm` with injected `LLMClient | None`)
- Create: `ilearn/agents/enhanced/recommendation.py` (port §2.2 core API; offline heuristic if no LLM)
- Create: `ilearn/agents/enhanced/question_generator.py` (port §3.2; offline stub items)
- Modify: `ilearn/agents/orchestrator.py` — only add gated optional calls after diagnosis/plan; **zero behavior change when flag false**
- Test: `tests/test_edition_0909_1_pr02.py`

**Interfaces:**
- Consumes: `is_enhanced_enabled`, `get/set_enhanced_profile`, `LLMClient`
- Produces: `EnhancedProfileUpdater.update(session, interaction) -> SessionState`
- Orchestrator: if not `ENABLE_ENHANCED_AGENTS`: never import side effects that alter papers

- [ ] **Step 1: Test flag-off orchestrator parity** — snapshot paper item ids before/after wiring with flag false
- [ ] **Step 2: Implement agents with offline stubs**
- [ ] **Step 3: Wire orchestrator behind flag**
- [ ] **Step 4: Test flag-on updates `metadata.enhanced`**
- [ ] **Step 5: `pytest tests/test_edition_0909_1_pr02.py tests/test_adaptive_api.py -q`**

---

### Task 5: PR #03 — API branches

**Files:**
- Modify: `ilearn/api/dashboard.py`
- Create: `ilearn/api/enhanced_report.py`
- Modify: `ilearn/api/app.py` include router
- Test: `tests/test_edition_0909_1_pr03.py`

**Interfaces:**
- Query `enhanced: bool = False` on summary / class overview
- If flag API false or query false → legacy response identical
- If both true → attach `enhanced_profile` + `suggestions` fields

- [ ] **Step 1: Tests for default == legacy**
- [ ] **Step 2: Implement branches + gated PDF**
- [ ] **Step 3: pytest PR03 + `tests/test_dashboard_api.py`**

---

### Task 6: Docs touch-up (after each PR lands)

**Files:**
- Modify: `VERSION.md` — add Edition 0909_1 PR#n row
- Optional: README capabilities note only after PR#03

---

## Self-Review

1. **Spec coverage:** §1.1→T2; storage/migration drop→T3; updater/IRT/rec/QG→T4; teacher API→T5; flags/rollback→T1. pyKT (§1.3) deferred as optional follow-up (not in user simplified 3-PR plan).
2. **Placeholders:** none intentional; PR#02 ports may trim unused pyKT to stub.
3. **Types:** `StudentFiveDimProfile` / `metadata.enhanced.schema_version==1` consistent across tasks.
