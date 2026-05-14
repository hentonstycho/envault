"""Integration-style tests: snapshot interacts with sync output."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from envault.snapshot import SnapshotError, load_snapshot, save_snapshot, snapshots_match
from envault.diff import compute_diff


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / ".envault" / "snapshots"


_INITIAL = {"API_KEY": "abc123", "DB_URL": "postgres://localhost/dev"}
_UPDATED = {"API_KEY": "xyz999", "DB_URL": "postgres://localhost/dev", "NEW_VAR": "hello"}


def test_no_change_detected_when_values_unchanged(snap_dir: Path):
    save_snapshot("dev", _INITIAL, snapshot_dir=snap_dir)
    snap = load_snapshot("dev", snapshot_dir=snap_dir)
    new_snap = save_snapshot("dev", _INITIAL, snapshot_dir=snap_dir)
    assert snapshots_match(snap, new_snap)


def test_change_detected_after_rotation(snap_dir: Path):
    old = save_snapshot("dev", _INITIAL, snapshot_dir=snap_dir)
    new = save_snapshot("dev", _UPDATED, snapshot_dir=snap_dir)
    assert not snapshots_match(old, new)


def test_snapshot_diff_reflects_added_and_changed_keys(snap_dir: Path, tmp_path: Path):
    """Snapshot values feed into compute_diff correctly."""
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=\"abc123\"\nDB_URL=\"postgres://localhost/dev\"\n")

    save_snapshot("dev", _INITIAL, snapshot_dir=snap_dir)

    diff = compute_diff(_UPDATED, env_file)
    assert "API_KEY" in diff.changed
    assert "NEW_VAR" in diff.added
    assert diff.has_changes


def test_overwrite_snapshot_updates_checksum(snap_dir: Path):
    first = save_snapshot("prod", _INITIAL, snapshot_dir=snap_dir)
    second = save_snapshot("prod", _UPDATED, snapshot_dir=snap_dir)
    loaded = load_snapshot("prod", snapshot_dir=snap_dir)
    assert loaded is not None
    assert loaded.checksum == second.checksum
    assert loaded.checksum != first.checksum


def test_multiple_profiles_isolated(snap_dir: Path):
    save_snapshot("dev", _INITIAL, snapshot_dir=snap_dir)
    save_snapshot("prod", _UPDATED, snapshot_dir=snap_dir)
    dev = load_snapshot("dev", snapshot_dir=snap_dir)
    prod = load_snapshot("prod", snapshot_dir=snap_dir)
    assert dev is not None and prod is not None
    assert not snapshots_match(dev, prod)
    assert dev.values == _INITIAL
    assert prod.values == _UPDATED
