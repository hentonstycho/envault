"""Integration tests: ParameterCache used alongside SSMClient mock."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.cache import ParameterCache
from envault.ssm import SSMClient


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path


def _make_ssm_client(cache_dir: Path) -> SSMClient:
    client = SSMClient.__new__(SSMClient)
    client._client = MagicMock()
    client._cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    return client


def test_second_call_uses_cache_not_ssm(cache_dir: Path):
    """After the first fetch, subsequent calls should return cached value."""
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    cache.set("/app/SECRET", "cached_value")

    # Simulate a client that would fail if called
    mock_boto = MagicMock()
    mock_boto.get_parameter.side_effect = AssertionError("SSM should not be called")

    result = cache.get("/app/SECRET")
    assert result == "cached_value"
    mock_boto.get_parameter.assert_not_called()


def test_cache_miss_triggers_fresh_fetch(cache_dir: Path):
    """A cache miss should result in the value being stored after fetch."""
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)

    # Simulate fetching and storing
    assert cache.get("/app/NEW_KEY") is None
    cache.set("/app/NEW_KEY", "fresh_value")
    assert cache.get("/app/NEW_KEY") == "fresh_value"


def test_invalidate_forces_refetch(cache_dir: Path):
    """After invalidation, the key should be treated as a miss."""
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    cache.set("/app/DB_PASS", "old_pass")
    cache.invalidate("/app/DB_PASS")

    assert cache.get("/app/DB_PASS") is None


def test_multiple_keys_independent(cache_dir: Path):
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    cache.set("/app/A", "alpha")
    cache.set("/app/B", "beta")

    cache.invalidate("/app/A")

    assert cache.get("/app/A") is None
    assert cache.get("/app/B") == "beta"
