"""Structured logging helpers for ILearn (sync-friendly)."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent basicConfig for the ilearn logger tree."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str = "ilearn") -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def log_execution(func: F) -> F:
    """Decorator: log start/finish/elapsed and re-raise failures."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger("ilearn.exec")
        logger.info("Executing %s", func.__name__)
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception("%s failed", func.__name__)
            raise
        elapsed = time.perf_counter() - start
        logger.info("%s completed in %.2fs", func.__name__, elapsed)
        return result

    return wrapper  # type: ignore[return-value]


class RetryHandler:
    """Synchronous retry helper with linear backoff."""

    @staticmethod
    def with_retry(
        func: Callable[[], Any],
        *,
        max_retries: int = 3,
        delay: float = 0.05,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> Any:
        logger = get_logger("ilearn.retry")
        last_error: BaseException | None = None
        for attempt in range(max_retries):
            try:
                return func()
            except exceptions as exc:
                last_error = exc
                logger.warning(
                    "Attempt %s/%s failed: %s", attempt + 1, max_retries, exc
                )
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
        assert last_error is not None
        raise last_error
