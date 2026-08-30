"""Tests for sync logging helpers."""

from __future__ import annotations

import pytest

from ilearn.core.logging_utils import RetryHandler, log_execution


def test_log_execution_returns_value():
    @log_execution
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, 2) == 3


def test_retry_eventually_succeeds():
    state = {"n": 0}

    def flaky() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("nope")
        return "ok"

    assert RetryHandler.with_retry(flaky, max_retries=3, delay=0.0) == "ok"


def test_retry_raises_after_exhaustion():
    def always_fail() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        RetryHandler.with_retry(always_fail, max_retries=2, delay=0.0)
