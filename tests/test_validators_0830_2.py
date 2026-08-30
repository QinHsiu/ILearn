"""Tests for submit validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ilearn.core.validators import (
    QuestionSubmission,
    StudentProfileUpdate,
    validate_submit_answers,
)


def test_validate_submit_allows_empty_answer():
    out = validate_submit_answers({"item_1": ""})
    assert out["item_1"] == ""


def test_validate_submit_rejects_xss():
    with pytest.raises(ValidationError):
        validate_submit_answers({"item_1": "<script>alert(1)</script>"})


def test_validate_submit_rejects_bad_id():
    with pytest.raises(ValidationError):
        QuestionSubmission(question_id="bad id!", answer="1")


def test_nickname_rejects_angle_brackets():
    with pytest.raises(ValidationError):
        StudentProfileUpdate(nickname='bad<name>')
