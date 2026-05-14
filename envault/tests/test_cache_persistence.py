"""Tests verifying that ParameterCache survives across instances (disk persistence)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from envault.cache import ParameterCache, CACHE_FILENAME


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_cache_reloaded_by_new_instance(cache_dir: Path):
    c1 = ParameterCache(cache_dir=cache_dir, ttl=300)
    c1.set("/app/TOKEN", "abc123")

    c2 = ParameterCache(cache_dir=cache_dir, ttl=300)
    assert c2.get("/app/TOKEN") == "abc123"


def test_cache_file_contains_expected_keys(cache_dir: Path):
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    cache.set("/app/X", "val_x")
    cache.set("/app/Y", "val_y")

    raw = json.loads((cache_dir / CACHE_FILENAME).read_text())
    assert set(raw.keys()) == {"/app/X", "/app/Y"}


def test_clear_removes_file_and_reloads_empty(cache_dir: Path):
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    cache.set("/app/Z", "val_z")
    cache.clear()

    c2 = ParameterCache(cache_dir=cache_dir, ttl=300)
    assert c2.get("/app/Z") is None


def test_new_instance_with_no_file_is_empty(cache_dir: Path):
    cache = ParameterCache(cache_dir=cache_dir, ttl=300)
    assert cache.get("/any/key") is None


def test_ttl_respected_across_instances(cache_dir: Path):
    import time

    c1 = ParameterCache(cache_dir=cache_dir, ttl=1)
    c1.set("/app/TEMP", "temporary")

    # Manually backdate the entry so it appears expired
    raw = json.loads((cache_dir / CACHE_FILENAME).read_text())
    raw["/app/TEMP"]["fetched_at"] = time.time() - 500
    (cache_dir / CACHE_FILENAME).write_text(json.dumps(raw))

    c2 = ParameterCache(cache_dir=cache_dir, ttl=1)
    assert c2.get("/app/TEMP") is None
