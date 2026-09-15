# Edition 0909_2 / PR02 Enhanced Agents Design

**Date:** 2026-09-09  
**Status:** Approved (Strategy A corrected)  
**Source:** `doc/edition_0909_2.txt`  
**Depends on:** PR #01 (`StudentFiveDimProfile`, `get/set_enhanced_profile`, `is_enhanced_enabled`)

## Goal

旁路注入增强 Agents（画像更新 / 推荐 / 出题 / 错因诊断），默认 Flag 关闭时对 `MultiAgentOrchestrator` 行为零副作用。

## Hard Constraints

1. `LLMClient | None` 注入；`stub_mode` 或不可用 LLM → 确定性 stub，不调网。
2. 画像仅经 PR #01：`get_enhanced_profile` / `set_enhanced_profile`（`SessionState`）。
3. Flag：`is_enhanced_enabled("ENABLE_ENHANCED_AGENTS")` 且 `ENABLE_ENHANCED_PROFILE`。
4. Orchestrator：仅在 `diagnose()`（及 `plan()`）末尾钩子；不新建双 route；签名与返回值不变。

## Modules

| File | Role |
| --- | --- |
| `ilearn/agents/enhanced/base.py` | `EnhancedAgentBase`, offline syllabus validator stub |
| `profile_updater.py` | Four sub-agents + signal extract (LLM or stub) |
| `recommend.py` | KP recommendations from mastery / weak concepts |
| `question.py` | One item stub/LLM for target KP |
| `diagnosis.py` | Error-type suggestions stub/LLM |
| `orchestrator.py` | `_maybe_update_enhanced_profile` after diagnose/plan |

## Acceptance

- Flag off → diagnose/plan identical side effects on `metadata` (no `enhanced` key from this path).
- Flag on + stub → `metadata.enhanced` written; no network.
