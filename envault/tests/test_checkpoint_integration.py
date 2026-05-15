"""Integration tests: checkpoint interacts with sync output."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.checkpoint import (
    Checkpoint,
    load_checkpoint,
    save_checkpoint,
    clear_checkpoint,
)


@pytest.fixture()
def chk_dir(tmp_path):
    return tmp_path / "cp"


def _fake_sync_and_checkpoint(chk_dir: Path, profile: str, param_count: int) -> Checkpoint:
    """Simulate what a real sync command would do after a successful sync."""
    cp = Checkpoint(
        profile=profile,
        synced_at=time.time(),
        env_file=".env",
        param_count=param_count,
    )
    save_checkpoint(chk_dir, cp)
    return cp


def test_checkpoint_recorded_after_sync(chk_dir):
    _fake_sync_and_checkpoint(chk_dir, "dev", param_count=5)
    loaded = load_checkpoint(chk_dir, "dev")
    assert loaded is not None
    assert loaded.param_count == 5


def test_checkpoint_age_grows_over_time(chk_dir):
    past = time.time() - 3600  # 1 hour ago
    cp = Checkpoint(profile="dev", synced_at=past, env_file=".env", param_count=2)
    save_checkpoint(chk_dir, cp)
    loaded = load_checkpoint(chk_dir, "dev")
    assert loaded.age_seconds() >= 3600


def test_multiple_profiles_stored_independently(chk_dir):
    _fake_sync_and_checkpoint(chk_dir, "dev", param_count=3)
    _fake_sync_and_checkpoint(chk_dir, "prod", param_count=10)
    dev = load_checkpoint(chk_dir, "dev")
    prod = load_checkpoint(chk_dir, "prod")
    assert dev.param_count == 3
    assert prod.param_count == 10


def test_clear_then_load_returns_none(chk_dir):
    _fake_sync_and_checkpoint(chk_dir, "staging", param_count=1)
    clear_checkpoint(chk_dir, "staging")
    assert load_checkpoint(chk_dir, "staging") is None


def test_extra_metadata_persisted(chk_dir):
    cp = Checkpoint(
        profile="dev",
        synced_at=time.time(),
        env_file=".env.dev",
        param_count=4,
        extra={"triggered_by": "ci", "run_id": "abc123"},
    )
    save_checkpoint(chk_dir, cp)
    loaded = load_checkpoint(chk_dir, "dev")
    assert loaded.extra["triggered_by"] == "ci"
    assert loaded.extra["run_id"] == "abc123"
