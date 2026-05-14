"""Lock file management for envault sync operations.

Prevents concurrent sync operations from corrupting .env files.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


LOCK_TIMEOUT_SECONDS = 30
LOCK_SUFFIX = ".envault.lock"


class LockError(Exception):
    """Raised when a lock cannot be acquired or is invalid."""


@dataclass
class LockFile:
    path: Path
    pid: int
    acquired_at: float

    def is_stale(self, timeout: float = LOCK_TIMEOUT_SECONDS) -> bool:
        """Return True if the lock is older than *timeout* seconds."""
        return (time.time() - self.acquired_at) > timeout

    def owned_by_us(self) -> bool:
        """Return True if the lock belongs to the current process."""
        return self.pid == os.getpid()


def _lock_path(env_path: Path) -> Path:
    return env_path.with_suffix(LOCK_SUFFIX)


def acquire(env_path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Path:
    """Acquire a lock for *env_path*.

    Returns the lock file path on success.
    Raises :class:`LockError` if an active lock held by another process exists.
    """
    lock = _lock_path(env_path)
    existing = read(lock)
    if existing is not None and not existing.owned_by_us():
        if not existing.is_stale(timeout):
            raise LockError(
                f"Lock held by PID {existing.pid} on '{env_path}'. "
                "Run 'envault unlock' or wait for it to expire."
            )
        # Stale lock — remove it and proceed.
        lock.unlink(missing_ok=True)

    lock.write_text(f"{os.getpid()}\n{time.time()}\n", encoding="utf-8")
    return lock


def release(env_path: Path) -> None:
    """Release the lock for *env_path* if we own it."""
    lock = _lock_path(env_path)
    existing = read(lock)
    if existing is not None and existing.owned_by_us():
        lock.unlink(missing_ok=True)


def read(lock_path: Path) -> Optional[LockFile]:
    """Parse a lock file. Returns None if the file does not exist."""
    if not lock_path.exists():
        return None
    try:
        parts = lock_path.read_text(encoding="utf-8").strip().splitlines()
        pid = int(parts[0])
        acquired_at = float(parts[1])
        return LockFile(path=lock_path, pid=pid, acquired_at=acquired_at)
    except (ValueError, IndexError) as exc:
        raise LockError(f"Corrupt lock file '{lock_path}': {exc}") from exc
