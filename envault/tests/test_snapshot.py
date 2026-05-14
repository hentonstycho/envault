"""Tests for envault.snapshot."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from envault.snapshot import (
    Snapshot,
    SnapshotError,
    _checksum,
    load_snapshot,
    save_snapshot,
    snapshots_match,
)


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


_VALUES = {"DB_HOST": "localhost", "DB_PORT": "5432", "SECRET": "hunter2"}


def test_checksum_deterministic():
    assert _checksum(_VALUES) == _checksum(_VALUES)


def test_checksum_order_independent():
    reversed_vals = dict(reversed(list(_VALUES.items())))
    assert _checksum(_VALUES) == _checksum(reversed_vals)


def test_checksum_changes_on_value_change():
    modified = {**_VALUES, "DB_PORT": "3306"}
    assert _checksum(_VALUES) != _checksum(modified)


def test_save_creates_file(snap_dir: Path):
    snap = save_snapshot("default", _VALUES, snapshot_dir=snap_dir)
    assert (snap_dir / "default.json").exists()
    assert snap.profile == "default"
    assert snap.keys == sorted(_VALUES.keys())


def test_save_and_load_roundtrip(snap_dir: Path):
    save_snapshot("default", _VALUES, snapshot_dir=snap_dir)
    loaded = load_snapshot("default", snapshot_dir=snap_dir)
    assert loaded is not None
    assert loaded.values == _VALUES
    assert loaded.checksum == _checksum(_VALUES)


def test_load_missing_returns_none(snap_dir: Path):
    result = load_snapshot("nonexistent", snapshot_dir=snap_dir)
    assert result is None


def test_load_corrupt_raises(snap_dir: Path):
    snap_dir.mkdir(parents=True)
    (snap_dir / "bad.json").write_text("{not valid json")
    with pytest.raises(SnapshotError, match="Corrupt snapshot"):
        load_snapshot("bad", snapshot_dir=snap_dir)


def test_snapshots_match_same_values(snap_dir: Path):
    a = save_snapshot("p", _VALUES, snapshot_dir=snap_dir)
    b = save_snapshot("p", _VALUES, snapshot_dir=snap_dir)
    assert snapshots_match(a, b)


def test_snapshots_differ_on_change(snap_dir: Path):
    a = save_snapshot("p", _VALUES, snapshot_dir=snap_dir)
    b = save_snapshot("p", {**_VALUES, "NEW_KEY": "val"}, snapshot_dir=snap_dir)
    assert not snapshots_match(a, b)


def test_snapshot_timestamp_is_recent(snap_dir: Path):
    before = time.time()
    snap = save_snapshot("ts", _VALUES, snapshot_dir=snap_dir)
    after = time.time()
    assert before <= snap.timestamp <= after
