"""Retry utilities with exponential backoff."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

import structlog

log = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff: str = "exponential"   # "exponential" | "linear" | "none"
    base_ms: float = 500
    max_ms: float = 10_000
    retriable_exceptions: tuple = (Exception,)


def with_retry(fn: Callable[[], T], policy: RetryPolicy) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except policy.retriable_exceptions as exc:
            last_exc = exc
            if attempt == policy.max_attempts:
                break
            delay = _delay(policy, attempt)
            log.warning("retry.backoff", attempt=attempt, delay_ms=delay, error=str(exc))
            time.sleep(delay / 1000)
    raise last_exc  # type: ignore[misc]


def _delay(policy: RetryPolicy, attempt: int) -> float:
    if policy.backoff == "exponential":
        return min(policy.base_ms * (2 ** (attempt - 1)), policy.max_ms)
    if policy.backoff == "linear":
        return min(policy.base_ms * attempt, policy.max_ms)
    return 0.0
