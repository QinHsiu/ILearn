"""Derivation rules for cross-template mastery — pure functions (no LLM)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ilearn.core.learner_state import LearnerState
from ilearn.orchestration.migration import DerivationSpec


def derive_mastery(
    state: LearnerState, spec: DerivationSpec, now: datetime
) -> tuple[float, dict[str, Any]]:
    """根据规则从源技能的证据重新推导目标掌握度。

    返回 (target_mastery, derivation_trace)。
    """
    sources = [state.mastery.get(s) for s in spec.source_skills]
    sources = [s for s in sources if s is not None]
    if not sources:
        base = spec.constant if spec.constant is not None else 0.0
        return base, {
            "rule": spec.rule,
            "source_skills": [],
            "inputs": [],
            "shrink_factor": 0.0,
            "target_skill": spec.target_skill,
        }

    trace_inputs = [
        {
            "skill": s.skill_id,
            "mastery": s.mastery,
            "evidence_count": s.evidence_count,
        }
        for s in sources
    ]

    if spec.rule == "constant":
        value = float(spec.constant or 0.0)
    elif spec.rule == "evidence_max":
        value = max(s.mastery for s in sources)
    elif spec.rule == "evidence_mean":
        value = sum(s.mastery for s in sources) / len(sources)
    elif spec.rule == "evidence_decay_mean":
        weighted, total = 0.0, 0.0
        for s in sources:
            age = (now - s.last_updated).total_seconds() / 86400.0
            w = 0.5 ** (max(age, 0.0) / spec.half_life_days)
            weighted += s.mastery * w
            total += w
        value = weighted / total if total else 0.0
    else:
        raise ValueError(f"unknown rule: {spec.rule}")

    total_evidence = sum(s.evidence_count for s in sources)
    shrink = min(1.0, total_evidence / 10.0)
    value = round(0.5 + (value - 0.5) * shrink, 4)

    trace = {
        "rule": spec.rule,
        "source_skills": list(spec.source_skills),
        "inputs": trace_inputs,
        "shrink_factor": round(shrink, 3),
        "target_skill": spec.target_skill,
    }
    return value, trace
