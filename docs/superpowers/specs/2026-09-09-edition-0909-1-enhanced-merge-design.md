# Edition 0909_1 Enhanced Merge Design

**Date:** 2026-09-09  
**Status:** Approved (A+C)  
**Source:** `doc/edition_0909_1.txt`  
**Target:** `D:\PycharmProjects\pythonProject\projects\ILearn`

## Goal

旁路合入 edition_0909_1 的五维画像、多 Agent 更新/推荐/出题、教师端增强能力；**默认关闭**，旧链路行为与测试基线不变。分 3 个独立 PR 合并，Flag 即可回滚。

## Hard Constraints

1. **路径重写：** 文档中的 `app/` → `ilearn/`；**不覆盖**现有文件。
2. **存储适配：** 不用 SQL 迁移；五维画像写入 `SessionState.metadata["enhanced"]`（JSON）。
3. **LLM 复用：** 统一 `ilearn.providers.llm.LLMClient`（及现有 FreeLLM 降级），不新建 `get_llm()`。

## Non-Goals (this merge)

- 不替换 `diagnosis.knowledge_mastery` / `SessionStore.list_all_metadata` 旧掌握度投影。
- 不引入 pyKT / SQLAlchemy 为硬依赖（知识追踪可在后续 PR 以 stub + optional extra 接入）。
- 不重写前端；API 先提供 `?enhanced=` 分支。

## Architecture

```
edition_0909_1 (app/*)
        │ path rewrite + adapters
        ▼
ilearn/core/models/enhanced_profile.py     # five-dim Pydantic
ilearn/core/enhanced_flags.py              # load data/features.yaml
ilearn/storage/sessions.py                 # + get/set metadata.enhanced (helpers)
ilearn/agents/enhanced/*                   # PR#02 gated agents
ilearn/api/dashboard.py                    # PR#03 ?enhanced= branches
        │
        ▼ Feature Flags (default false)
ENABLE_ENHANCED_PROFILE | AGENTS | API
        │
        ▼ if false → 100% legacy orchestrator / dashboard
```

### Naming

| Edition (`app/`) | ILearn path | Notes |
| --- | --- | --- |
| `models/student_profile.py` | `ilearn/core/models/enhanced_profile.py` | Keep `StudentFiveDimProfile`; module-local `CognitiveDimension` **BaseModel** must not be confused with `ilearn.core.cognitive_profile.CognitiveDimension` **Enum** (Bloom). Adapters import with aliases. |
| `services/profile_updater.py` | `ilearn/agents/enhanced/profile_updater.py` | PR#02 |
| `services/irt_adaptive.py` etc. | `ilearn/agents/enhanced/*.py` | PR#02; behind `ENABLE_ENHANCED_AGENTS` |
| `api/v1/endpoints/teacher.py` | extend `ilearn/api/dashboard.py` | PR#03; no second auth stack |
| SQL migration `002_*` | **dropped** | replaced by `metadata.enhanced` |

### Storage shape

```json
{
  "metadata": {
    "enhanced": {
      "profile": { "...StudentFiveDimProfile.model_dump()..." },
      "schema_version": 1
    }
  }
}
```

- Flag off: never write `metadata.enhanced` from core paths.
- Flag on: `ProfileStore` / SessionStore helpers read-modify-write only the `enhanced` key; other metadata keys untouched.
- Legacy mastery continues to come from `session.diagnosis.knowledge_mastery` (and dashboard `SessionMetadata` projection).

### Feature flags

File: `data/features.yaml` (new; defaults all `false`)

```yaml
ENABLE_ENHANCED_PROFILE: false
ENABLE_ENHANCED_AGENTS: false
ENABLE_ENHANCED_API: false
```

Loader: `ilearn/core/enhanced_flags.py` — env override `ILEARN_<FLAG>=1` wins over YAML for ops kill-switch.

Dependency: `ENABLE_ENHANCED_AGENTS` / `ENABLE_ENHANCED_API` imply profile storage available; if profile flag is false, agents/API enhanced branches no-op to legacy.

## PR Breakdown

### PR #01 — Data model + storage

- Create `ilearn/core/models/__init__.py`, `enhanced_profile.py` (from edition §1.1).
- Create `ProfileAdapter`: `StudentProfile` + optional `DiagnosisReport` / `LearnerPortrait` ↔ `StudentFiveDimProfile`.
- Session helpers: `get_enhanced_blob(session)`, `set_enhanced_profile(session, profile)` writing `metadata["enhanced"]`.
- `data/features.yaml` + `enhanced_flags.is_enabled(...)`.
- Tests: round-trip JSON; flag off leaves metadata absent; diagnosis mastery / `list_all_metadata` unchanged.

### PR #02 — Multi-agent injection

- Package `ilearn/agents/enhanced/` (profile updater, recommendation, question gen stubs from edition modules 1.2 / 2 / 3 — offline-safe stubs when LLM unavailable).
- Orchestrator: **conditional register only**; flag false → byte-identical legacy call graph for assessment/diagnosis/plan outputs in tests.
- No change to default assessment paper size / phase machine.

### PR #03 — API extension

- `dashboard.py` / summary endpoints: `?enhanced=true` only when `ENABLE_ENHANCED_API`; else ignore param and return legacy payloads.
- `GET /enhanced/report` (or under sessions) PDF export gated; default routes unchanged.

## Rollback

Turn flags to `false` in `data/features.yaml` or unset env overrides — instant legacy path; no code revert required.

## Acceptance (user)

| PR | Criterion |
| --- | --- |
| #01 | Session JSON can persist `metadata.enhanced`; legacy mastery projection unaffected |
| #02 | Flag off → orchestrator items/recommendations match baseline; flag on → new agents callable |
| #03 | `enhanced=false`/default → old data; `enhanced=true` → five-dim + personalized suggestions |

## Risks

- **Name clash** Bloom `CognitiveDimension` Enum vs five-dim BaseModel — always alias imports.
- **Edition code quality** (bare `json.loads` on LLM output, numpy deps) — PR#02 wraps with try/offline fallbacks; do not let exceptions escape into legacy path.
- **Test count baseline** — all new tests must pass with flags default false without changing existing assertions.
