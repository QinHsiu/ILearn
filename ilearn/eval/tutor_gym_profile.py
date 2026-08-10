"""TutorGym-style step completeness metrics for constructed responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.grading import StepGrader
from ilearn.core.schemas import AssessmentItem
from ilearn.providers.llm import LLMClient

__all__ = ["StepCompletenessProfile", "run_completeness_benchmark", "score_profile"]


class StepCompletenessProfile(BaseModel):
    item_id: str
    legal_step_indices: list[int] = Field(default_factory=list)
    student_step_indices: list[int] = Field(default_factory=list)
    step_scores: list[float] = Field(default_factory=list)
    stem: str | None = None
    answer_key: str | None = None
    rubric_steps: list[str] = Field(default_factory=list)
    student_steps: list[str] = Field(default_factory=list)


def load_completeness_profiles(path: Path) -> list[StepCompletenessProfile]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("profiles file must contain a JSON array")
    return [StepCompletenessProfile.model_validate(entry) for entry in raw]


def score_profile(profile: StepCompletenessProfile) -> dict[str, float]:
    """Score one tutor_gym-style profile for completeness and step quality."""
    legal = set(profile.legal_step_indices)
    student = set(profile.student_step_indices)
    completeness = len(student & legal) / len(legal) if legal else 0.0

    if profile.step_scores:
        avg_step_score = sum(profile.step_scores) / len(profile.step_scores)
    else:
        avg_step_score = completeness

    correctness = (
        1.0
        if completeness >= 1.0 and profile.step_scores and all(s >= 1.0 for s in profile.step_scores)
        else 0.0
        if profile.step_scores
        else completeness
    )
    return {
        "completeness": completeness,
        "correctness": correctness,
        "avg_step_score": avg_step_score,
    }


def _grade_step_scores(
    profile: StepCompletenessProfile,
    *,
    grader: StepGrader,
) -> list[float]:
    if not profile.rubric_steps or not profile.student_steps:
        return profile.step_scores
    item = AssessmentItem(
        id=profile.item_id,
        stem=profile.stem or profile.item_id,
        type="constructed",
        difficulty="easy",
        knowledge_ids=["eval"],
        answer_key=profile.answer_key,
        rubric_steps=profile.rubric_steps,
    )
    answer_text = "\n".join(profile.student_steps)
    result = grader.grade_item(item, answer_text)
    scores: list[float] = []
    for index in profile.student_step_indices:
        if index < len(result.step_results):
            status = result.step_results[index].status
            scores.append(1.0 if status == "correct" else 0.5 if status == "partial" else 0.0)
        else:
            scores.append(0.0)
    return scores or profile.step_scores


def run_completeness_benchmark(
    profiles_path: Path,
    *,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Aggregate completeness metrics over tutor_gym-style profiles."""
    profiles = load_completeness_profiles(profiles_path)
    if not profiles:
        return {
            "total": 0,
            "completeness": 0.0,
            "correctness": 0.0,
            "avg_step_score": 0.0,
        }

    grader = StepGrader(llm)
    completeness_vals: list[float] = []
    correctness_vals: list[float] = []
    avg_step_vals: list[float] = []

    for profile in profiles:
        scored_profile = profile
        if grader._llm_available() and profile.rubric_steps:
            scores = _grade_step_scores(profile, grader=grader)
            scored_profile = profile.model_copy(update={"step_scores": scores})
        metrics = score_profile(scored_profile)
        completeness_vals.append(metrics["completeness"])
        correctness_vals.append(metrics["correctness"])
        avg_step_vals.append(metrics["avg_step_score"])

    return {
        "total": len(profiles),
        "completeness": sum(completeness_vals) / len(completeness_vals),
        "correctness": sum(correctness_vals) / len(correctness_vals),
        "avg_step_score": sum(avg_step_vals) / len(avg_step_vals),
    }
