"""Frustration-aware replan triggers and planner adjustments."""

from __future__ import annotations

from ilearn.core.schemas import DiagnosisReport, LearnerPortrait

_FRUSTRATION_THRESHOLD = 0.3
_HINT_DEPENDENCY_THRESHOLD = 0.4
_CONFIDENCE_TASK = "信心重建：回顾已掌握例题"


def should_replan(portrait: LearnerPortrait, diagnosis: DiagnosisReport) -> bool:
    """True when learner signals frustration, hint dependency, or probe gap."""
    if portrait.dimensions.emotional.get("frustration", 0.0) >= _FRUSTRATION_THRESHOLD:
        return True
    if portrait.dimensions.behavioral.get("hint_dependency", 0.0) >= _HINT_DEPENDENCY_THRESHOLD:
        return True
    return "practice_probe_gap" in diagnosis.flags


def replan_adjustments(diagnosis: DiagnosisReport) -> dict:
    """Return planner tweaks for a frustration-aware replan."""
    _ = diagnosis
    return {"easier_focus": True, "confidence_task": _CONFIDENCE_TASK}
