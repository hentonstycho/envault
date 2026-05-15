"""Tests for envault.throttle (TokenBucket + with_backoff)."""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest

from envault.throttle import TokenBucket, ThrottleError, with_backoff


# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------


def test_token_bucket_acquires_immediately_when_full():
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    start = time.monotonic()
    bucket.acquire(1.0)
    elapsed = time.monotonic() - start
    assert elapsed < 0.05  # should not sleep


def test_token_bucket_raises_when_tokens_exceed_capacity():
    bucket = TokenBucket(rate=1.0, capacity=5.0)
    with pytest.raises(ThrottleError, match="exceeds bucket capacity"):
        bucket.acquire(6.0)


def test_token_bucket_sleeps_when_tokens_depleted():
    """Patch time.sleep so the test stays fast."""
    bucket = TokenBucket(rate=2.0, capacity=1.0)
    # Drain the bucket
    bucket._tokens = 0.0
    bucket._last = time.monotonic()

    sleep_calls: list[float] = []

    real_monotonic = time.monotonic
    call_count = 0

    def fake_monotonic() -> float:
        nonlocal call_count
        call_count += 1
        # First call inside acquire → no time has passed; second → 1 s passed
        return real_monotonic() if call_count <= 1 else real_monotonic() + 1.0

    with patch("envault.throttle.time.sleep", side_effect=lambda s: sleep_calls.append(s)), \
         patch("envault.throttle.time.monotonic", side_effect=fake_monotonic):
        bucket.acquire(1.0)

    assert len(sleep_calls) >= 1
    assert all(s >= 0 for s in sleep_calls)


def test_token_bucket_multiple_acquires_drain_correctly():
    bucket = TokenBucket(rate=100.0, capacity=5.0)
    for _ in range(5):
        bucket.acquire(1.0)
    assert bucket._tokens < 1.0


# ---------------------------------------------------------------------------
# with_backoff
# ---------------------------------------------------------------------------


def test_with_backoff_returns_on_first_success():
    fn = MagicMock(return_value=42)
    result = with_backoff(fn, retries=3, base_delay=0)
    assert result == 42
    fn.assert_called_once()


def test_with_backoff_retries_on_retryable_exception():
    fn = MagicMock(side_effect=[ValueError("boom"), ValueError("boom"), "ok"])
    with patch("envault.throttle.time.sleep"):
        result = with_backoff(fn, retries=3, base_delay=0.0, retryable=ValueError)
    assert result == "ok"
    assert fn.call_count == 3


def test_with_backoff_raises_after_exhausting_retries():
    fn = MagicMock(side_effect=ValueError("always fails"))
    with patch("envault.throttle.time.sleep"), pytest.raises(ValueError, match="always fails"):
        with_backoff(fn, retries=2, base_delay=0.0, retryable=ValueError)
    assert fn.call_count == 3  # initial + 2 retries


def test_with_backoff_does_not_catch_non_retryable():
    fn = MagicMock(side_effect=RuntimeError("not retryable"))
    with pytest.raises(RuntimeError):
        with_backoff(fn, retries=3, base_delay=0.0, retryable=ValueError)
    fn.assert_called_once()


def test_with_backoff_respects_max_delay():
    delays: list[float] = []
    fn = MagicMock(side_effect=[OSError()] * 4 + ["done"])
    with patch("envault.throttle.time.sleep", side_effect=lambda d: delays.append(d)):
        with_backoff(
            fn,
            retries=4,
            base_delay=1.0,
            max_delay=3.0,
            backoff_factor=2.0,
            retryable=OSError,
        )
    assert all(d <= 3.0 for d in delays)
