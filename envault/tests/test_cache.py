"""Tests for envault.cache."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from envault.cache import CacheEntry, ParameterCache, DEFAULT_TTL, CACHE_FILENAME


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def cache(cache_dir: Path) -> ParameterCache:
    return ParameterCache(cache_dir=cache_dir, ttl=60)


# --- CacheEntry ---

def test_entry_not_expired_when_fresh():
    entry = CacheEntry(value="secret", fetched_at=time.time(), ttl=60)
    assert not entry.is_expired()


def test_entry_expired_when_old():
    entry = CacheEntry(value="secret", fetched_at=time.time() - 120, ttl=60)
    assert entry.is_expired()


def test_entry_roundtrip():
    entry = CacheEntry(value="val", fetched_at=1234567890.0, ttl=120)
    restored = CacheEntry.from_dict(entry.to_dict())
    assert restored.value == entry.value
    assert restored.fetched_at == entry.fetched_at
    assert restored.ttl == entry.ttl


# --- ParameterCache ---

def test_get_returns_none_for_missing_key(cache: ParameterCache):
    assert cache.get("/app/SECRET") is None


def test_set_and_get(cache: ParameterCache):
    cache.set("/app/SECRET", "hunter2")
    assert cache.get("/app/SECRET") == "hunter2"


def test_set_persists_to_disk(cache_dir: Path, cache: ParameterCache):
    cache.set("/app/KEY", "value")
    raw = json.loads((cache_dir / CACHE_FILENAME).read_text())
    assert "/app/KEY" in raw


def test_get_returns_none_for_expired_entry(cache_dir: Path):
    c = ParameterCache(cache_dir=cache_dir, ttl=1)
    c.set("/app/KEY", "value")
    # Manually expire by overwriting fetched_at
    raw = json.loads((cache_dir / CACHE_FILENAME).read_text())
    raw["/app/KEY"]["fetched_at"] = time.time() - 999
    (cache_dir / CACHE_FILENAME).write_text(json.dumps(raw))
    c2 = ParameterCache(cache_dir=cache_dir, ttl=1)
    assert c2.get("/app/KEY") is None


def test_invalidate_removes_key(cache: ParameterCache):
    cache.set("/app/KEY", "value")
    cache.invalidate("/app/KEY")
    assert cache.get("/app/KEY") is None


def test_clear_removes_all_entries(cache: ParameterCache, cache_dir: Path):
    cache.set("/app/A", "1")
    cache.set("/app/B", "2")
    cache.clear()
    assert cache.get("/app/A") is None
    assert not (cache_dir / CACHE_FILENAME).exists()


def test_load_survives_corrupt_cache(cache_dir: Path):
    (cache_dir / CACHE_FILENAME).write_text("not valid json{{{")
    c = ParameterCache(cache_dir=cache_dir)
    assert c.get("/any") is None
