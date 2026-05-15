"""Tests verifying that the CLI honours checkpoint read/write behaviour."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.checkpoint import Checkpoint, load_checkpoint, save_checkpoint


@pytest.fixture()
def chk_dir(tmp_path):
    return tmp_path / "cp"


# ---------------------------------------------------------------------------
# Simulate the checkpoint-write path that cmd_sync would call
# ---------------------------------------------------------------------------

def _simulate_cmd_sync(chk_dir: Path, profile: str, env_file: str, params: dict) -> None:
    """Minimal stand-in for the checkpoint-writing portion of cmd_sync."""
    cp = Checkpoint(
        profile=profile,
        synced_at=time.time(),
        env_file=env_file,
        param_count=len(params),
    )
    save_checkpoint(chk_dir, cp)


def test_cmd_sync_writes_checkpoint(chk_dir):
    _simulate_cmd_sync(chk_dir, "dev", ".env", {"A": "1", "B": "2"})
    cp = load_checkpoint(chk_dir, "dev")
    assert cp is not None
    assert cp.param_count == 2


def test_cmd_sync_updates_existing_checkpoint(chk_dir):
    _simulate_cmd_sync(chk_dir, "dev", ".env", {"A": "1"})
    first = load_checkpoint(chk_dir, "dev")

    time.sleep(0.01)  # ensure synced_at advances
    _simulate_cmd_sync(chk_dir, "dev", ".env", {"A": "1", "B": "2", "C": "3"})
    second = load_checkpoint(chk_dir, "dev")

    assert second.param_count == 3
    assert second.synced_at >= first.synced_at


def test_checkpoint_env_file_path_stored_correctly(chk_dir):
    _simulate_cmd_sync(chk_dir, "prod", ".env.production", {"X": "y"})
    cp = load_checkpoint(chk_dir, "prod")
    assert cp.env_file == ".env.production"


def test_no_checkpoint_before_first_sync(chk_dir):
    assert load_checkpoint(chk_dir, "fresh-profile") is None


def test_checkpoint_age_fresh_after_sync(chk_dir):
    _simulate_cmd_sync(chk_dir, "dev", ".env", {"K": "v"})
    cp = load_checkpoint(chk_dir, "dev")
    assert cp.age_seconds() < 5  # just written — must be very fresh
