"""Tests for envault.rotate."""
from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path

import pytest

from envault.rotate import RotationReport, RotationStatus, check_rotation


@pytest.fixture()
def audit_file(tmp_path: Path) -> str:
    return str(tmp_path / "audit.jsonl")


def _write_entry(
    audit_file: str,
    path: str,
    action: str,
    days_ago: float,
) -> None:
    ts = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
        days=days_ago
    )
    entry = {"path": path, "action": action, "timestamp": ts.isoformat()}
    with open(audit_file, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# RotationStatus.summary
# ---------------------------------------------------------------------------

def test_summary_never_synced() -> None:
    s = RotationStatus(
        path="/app/secret",
        last_synced=None,
        age_days=None,
        is_stale=True,
        threshold_days=30,
    )
    assert "never synced" in s.summary()


def test_summary_stale() -> None:
    last = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    s = RotationStatus(
        path="/app/secret",
        last_synced=last,
        age_days=45.0,
        is_stale=True,
        threshold_days=30,
    )
    assert "[STALE]" in s.summary()


def test_summary_fresh() -> None:
    last = datetime.datetime.now(tz=datetime.timezone.utc)
    s = RotationStatus(
        path="/app/secret",
        last_synced=last,
        age_days=2.0,
        is_stale=False,
        threshold_days=30,
    )
    assert "[STALE]" not in s.summary()


# ---------------------------------------------------------------------------
# check_rotation
# ---------------------------------------------------------------------------

def test_never_synced_is_stale(audit_file: str) -> None:
    report = check_rotation(["/app/db"], audit_file)
    assert report.has_stale
    assert report.statuses[0].last_synced is None


def test_recent_sync_not_stale(audit_file: str) -> None:
    _write_entry(audit_file, "/app/db", "sync", days_ago=5)
    report = check_rotation(["/app/db"], audit_file, threshold_days=30)
    assert not report.has_stale
    assert report.statuses[0].age_days is not None
    assert report.statuses[0].age_days < 6


def test_old_sync_is_stale(audit_file: str) -> None:
    _write_entry(audit_file, "/app/db", "sync", days_ago=45)
    report = check_rotation(["/app/db"], audit_file, threshold_days=30)
    assert report.has_stale
    assert "/app/db" in report.stale_paths


def test_multiple_paths_mixed(audit_file: str) -> None:
    _write_entry(audit_file, "/app/fresh", "sync", days_ago=1)
    _write_entry(audit_file, "/app/stale", "sync", days_ago=60)
    report = check_rotation(["/app/fresh", "/app/stale"], audit_file, threshold_days=30)
    assert "/app/stale" in report.stale_paths
    assert "/app/fresh" not in report.stale_paths


def test_non_sync_action_ignored(audit_file: str) -> None:
    _write_entry(audit_file, "/app/db", "check", days_ago=1)
    report = check_rotation(["/app/db"], audit_file)
    assert report.statuses[0].last_synced is None


def test_latest_entry_used(audit_file: str) -> None:
    _write_entry(audit_file, "/app/db", "sync", days_ago=50)
    _write_entry(audit_file, "/app/db", "sync", days_ago=2)
    report = check_rotation(["/app/db"], audit_file, threshold_days=30)
    assert not report.has_stale
