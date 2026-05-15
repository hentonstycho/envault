"""Rate-limiting / back-off helpers for AWS SSM API calls.

Provides a simple token-bucket throttle and an exponential-backoff
retry wrapper so that bulk syncs don't hammer the SSM endpoint.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ThrottleError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


@dataclass
class TokenBucket:
    """Token-bucket rate limiter.

    Args:
        rate:     tokens added per second.
        capacity: maximum burst size (tokens).
    """

    rate: float
    capacity: float
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> None:
        """Block until *tokens* are available."""
        if tokens > self.capacity:
            raise ThrottleError(
                f"Requested {tokens} tokens exceeds bucket capacity {self.capacity}"
            )
        while True:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            deficit = tokens - self._tokens
            sleep_for = deficit / self.rate
            log.debug("ThrottleBucket: sleeping %.3fs to acquire %.1f tokens", sleep_for, tokens)
            time.sleep(sleep_for)


def with_backoff(
    fn: Callable[[], T],
    *,
    retries: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> T:
    """Call *fn* with exponential back-off on *retryable* exceptions."""
    delay = base_delay
    for attempt in range(retries + 1):
        try:
            return fn()
        except retryable as exc:  # type: ignore[misc]
            if attempt == retries:
                raise
            log.warning(
                "Attempt %d/%d failed (%s). Retrying in %.2fs…",
                attempt + 1,
                retries,
                exc,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    raise RuntimeError("unreachable")  # pragma: no cover
