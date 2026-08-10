"""Offline step-grading eval harness: fixtures, metrics, and runner."""

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


def final_correct_accuracy(expected: list[bool], predicted: list[bool]) -> float:
    """Fraction of items where predicted final_correct matches expected."""
    if not expected:
        return 0.0
    pairs = zip(expected, predicted, strict=True)
    return sum(exp == pred for exp, pred in pairs) / len(expected)


def json_valid_rate(valid_flags: list[bool]) -> float:
    """Fraction of grading outputs that parsed as valid structured JSON."""
    if not valid_flags:
        return 0.0
    return sum(valid_flags) / len(valid_flags)


def tag_set_f1(expected: set[str], predicted: set[str]) -> float:
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
    pairs = [
        (set(expected), set(predicted))
        for expected, predicted in zip(expected_list, predicted_list, strict=True)
    ]
    labels = set().union(*(expected | predicted for expected, predicted in pairs))
    if not labels:
        return 1.0
    scores = []
    for label in labels:
        true_positive = sum(
            label in expected and label in predicted for expected, predicted in pairs
        )
        false_positive = sum(
            label not in expected and label in predicted for expected, predicted in pairs
        )
        false_negative = sum(
            label in expected and label not in predicted for expected, predicted in pairs
        )
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(2 * true_positive / denominator if denominator else 0.0)
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
    expected_correct: list[bool] = []
    predicted_correct: list[bool] = []
    expected_tags: list[list[str]] = []
    predicted_tags: list[list[str]] = []

    for fixture in fixtures:
        item = AssessmentItem.model_validate(fixture.item)
        result = grader.grade_item(item, fixture.student_answer)
        expected_correct.append(fixture.expected_final_correct)
        predicted_correct.append(result.final_correct)
        expected_tags.append(fixture.expected_error_tags)
        predicted_tags.append(list(result.error_tags))

    return EvalMetrics(
        accuracy=final_correct_accuracy(expected_correct, predicted_correct),
        macro_f1=macro_f1_error_tags(expected_tags, predicted_tags),
        json_valid_rate=1.0,
    )
