"""Minimal step-grading eval runner (Task 10 will expand fixtures and tests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.grading import StepGrader
from ilearn.core.schemas import AssessmentItem


class GradingFixture(BaseModel):
    id: str
    item: dict[str, Any]
    student_answer: str
    expected_final_correct: bool
    expected_error_tags: list[str] = Field(default_factory=list)


class EvalMetrics(BaseModel):
    accuracy: float
    macro_f1: float
    json_valid_rate: float


def _tag_set_f1(expected: set[str], predicted: set[str]) -> float:
    if not expected and not predicted:
        return 1.0
    if not expected or not predicted:
        return 0.0
    tp = len(expected & predicted)
    if tp == 0:
        return 0.0
    precision = tp / len(predicted)
    recall = tp / len(expected)
    return 2 * precision * recall / (precision + recall)


def macro_f1_error_tags(
    expected_list: list[list[str]], predicted_list: list[list[str]]
) -> float:
    if not expected_list:
        return 0.0
    pairs = zip(expected_list, predicted_list, strict=True)
    scores = [_tag_set_f1(set(exp), set(pred)) for exp, pred in pairs]
    return sum(scores) / len(scores)


def load_fixtures(path: Path) -> list[GradingFixture]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("fixtures file must contain a JSON array")
    return [GradingFixture.model_validate(entry) for entry in raw]


def run_eval(
    fixtures_path: Path,
    grader: StepGrader | None = None,
) -> EvalMetrics:
    fixtures = load_fixtures(fixtures_path)
    if not fixtures:
        return EvalMetrics(accuracy=0.0, macro_f1=0.0, json_valid_rate=0.0)

    grader = grader or StepGrader(None)
    correct = 0
    expected_tags: list[list[str]] = []
    predicted_tags: list[list[str]] = []

    for fixture in fixtures:
        item = AssessmentItem.model_validate(fixture.item)
        result = grader.grade_item(item, fixture.student_answer)
        if result.final_correct == fixture.expected_final_correct:
            correct += 1
        expected_tags.append(fixture.expected_error_tags)
        predicted_tags.append(list(result.error_tags))

    total = len(fixtures)
    return EvalMetrics(
        accuracy=correct / total,
        macro_f1=macro_f1_error_tags(expected_tags, predicted_tags),
        json_valid_rate=1.0,
    )
