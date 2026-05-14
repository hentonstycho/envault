"""Tests for envault.lock."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from envault.lock import (
    LockError,
    LockFile,
    acquire,
    read,
    release,
    _lock_path,
    LOCK_TIMEOUT_SECONDS,
)


@pytest.fixture()
def env_file(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.touch()
    return p


# ---------------------------------------------------------------------------
# read()
# ---------------------------------------------------------------------------

def test_read_returns_none_when_no_lock(env_file: Path) -> None:
    assert read(_lock_path(env_file)) is None


def test_read_parses_valid_lock(env_file: Path) -> None:
    lock_path = _lock_path(env_file)
    lock_path.write_text(f"1234\n{time.time()}\n", encoding="utf-8")
    lf = read(lock_path)
    assert lf is not None
    assert lf.pid == 1234


def test_read_raises_on_corrupt_lock(env_file: Path) -> None:
    lock_path = _lock_path(env_file)
    lock_path.write_text("not-a-pid\n", encoding="utf-8")
    with pytest.raises(LockError, match="Corrupt"):
        read(lock_path)


# ---------------------------------------------------------------------------
# acquire() / release()
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(env_file: Path) -> None:
    lock_path = acquire(env_file)
    assert lock_path.exists()


def test_acquire_records_current_pid(env_file: Path) -> None:
    lock_path = acquire(env_file)
    lf = read(lock_path)
    assert lf is not None
    assert lf.pid == os.getpid()


def test_release_removes_lock(env_file: Path) -> None:
    acquire(env_file)
    release(env_file)
    assert not _lock_path(env_file).exists()


def test_release_noop_when_no_lock(env_file: Path) -> None:
    # Should not raise.
    release(env_file)


def test_acquire_raises_when_other_process_holds_lock(env_file: Path) -> None:
    lock_path = _lock_path(env_file)
    # Simulate a lock from a different (non-existent) PID held just now.
    lock_path.write_text(f"99999999\n{time.time()}\n", encoding="utf-8")
    with pytest.raises(LockError, match="Lock held by PID"):
        acquire(env_file)


def test_acquire_removes_stale_lock_and_succeeds(env_file: Path) -> None:
    lock_path = _lock_path(env_file)
    stale_time = time.time() - LOCK_TIMEOUT_SECONDS - 1
    lock_path.write_text(f"99999999\n{stale_time}\n", encoding="utf-8")
    acquired = acquire(env_file)
    lf = read(acquired)
    assert lf is not None
    assert lf.pid == os.getpid()


# ---------------------------------------------------------------------------
# LockFile helpers
# ---------------------------------------------------------------------------

def test_is_stale_false_for_fresh_lock() -> None:
    lf = LockFile(path=Path("/tmp/x.lock"), pid=1, acquired_at=time.time())
    assert not lf.is_stale()


def test_is_stale_true_for_old_lock() -> None:
    old = time.time() - LOCK_TIMEOUT_SECONDS - 5
    lf = LockFile(path=Path("/tmp/x.lock"), pid=1, acquired_at=old)
    assert lf.is_stale()
