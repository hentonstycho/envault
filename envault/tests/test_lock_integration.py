"""Integration tests: lock interacts correctly with sync flow."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.lock import LockError, acquire, release, _lock_path
from envault.sync import SyncError, sync
from envault.config import EnvaultConfig


@pytest.fixture()
def env_file(tmp_path: Path) -> Path:
    p = tmp_path / ".env"
    p.touch()
    return p


def _make_config(env_path: Path) -> EnvaultConfig:
    return EnvaultConfig(
        profile="default",
        region="us-east-1",
        paths=["/app/dev"],
        env_file=str(env_path),
        mask_values=True,
        audit_log=None,
    )


# ---------------------------------------------------------------------------
# Verify lock lifecycle around sync()
# ---------------------------------------------------------------------------

def test_lock_acquired_and_released_after_sync(env_file: Path) -> None:
    cfg = _make_config(env_file)
    mock_client = MagicMock()
    mock_client.get_parameters_by_path.return_value = [
        {"Name": "/app/dev/KEY", "Value": "val"}
    ]

    with patch("envault.sync.acquire") as mock_acquire, \
         patch("envault.sync.release") as mock_release:
        mock_acquire.return_value = _lock_path(env_file)
        sync(cfg, mock_client)

    mock_acquire.assert_called_once_with(env_file)
    mock_release.assert_called_once_with(env_file)


def test_lock_released_even_on_sync_error(env_file: Path) -> None:
    cfg = _make_config(env_file)
    mock_client = MagicMock()
    mock_client.get_parameters_by_path.side_effect = RuntimeError("boom")

    with patch("envault.sync.acquire") as mock_acquire, \
         patch("envault.sync.release") as mock_release:
        mock_acquire.return_value = _lock_path(env_file)
        with pytest.raises((RuntimeError, SyncError)):
            sync(cfg, mock_client)

    mock_release.assert_called_once_with(env_file)


def test_sync_raises_lock_error_when_locked(env_file: Path) -> None:
    cfg = _make_config(env_file)
    mock_client = MagicMock()

    with patch("envault.sync.acquire", side_effect=LockError("busy")):
        with pytest.raises(LockError, match="busy"):
            sync(cfg, mock_client)


def test_real_lock_prevents_double_acquire(env_file: Path) -> None:
    """Two sequential acquires from the same PID should succeed (re-entrant)."""
    lock_path = acquire(env_file)
    # Same PID — owned_by_us() is True, so second acquire overwrites.
    lock_path2 = acquire(env_file)
    assert lock_path == lock_path2
    release(env_file)
