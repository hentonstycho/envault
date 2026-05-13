"""Tests for envault.sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.config import EnvaultConfig
from envault.ssm import SSMError
from envault.sync import SyncError, _format_env_line, sync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, **overrides) -> EnvaultConfig:
    defaults = dict(
        aws_region="us-east-1",
        aws_profile=None,
        env_file=str(tmp_path / ".env"),
        parameters=[{"path": "/app/DB_URL", "env_var": "DATABASE_URL"}],
        paths=[],
    )
    defaults.update(overrides)
    return EnvaultConfig(**defaults)


def _mock_client(param_values: dict[str, str] | None = None, path_values: dict[str, str] | None = None) -> MagicMock:
    client = MagicMock()
    client.get_parameter.side_effect = lambda p: (param_values or {})[p]
    client.get_parameters_by_path.side_effect = lambda p: (path_values or {})
    return client


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_format_env_line_simple():
    assert _format_env_line("KEY", "value") == 'KEY="value"'


def test_format_env_line_escapes_quotes():
    assert _format_env_line("K", 'say "hi"') == 'K="say \\"hi\\""'


def test_sync_writes_env_file(tmp_path):
    config = _make_config(tmp_path)
    client = _mock_client(param_values={"/app/DB_URL": "postgres://localhost/db"})

    result = sync(config, client=client)

    assert result == {"DATABASE_URL": "postgres://localhost/db"}
    env_file = Path(config.env_file)
    assert env_file.exists()
    assert 'DATABASE_URL="postgres://localhost/db"' in env_file.read_text()


def test_sync_dry_run_does_not_write(tmp_path):
    config = _make_config(tmp_path)
    client = _mock_client(param_values={"/app/DB_URL": "postgres://localhost/db"})

    result = sync(config, client=client, dry_run=True)

    assert result == {"DATABASE_URL": "postgres://localhost/db"}
    assert not Path(config.env_file).exists()


def test_sync_path_parameters(tmp_path):
    config = _make_config(
        tmp_path,
        parameters=[],
        paths=[{"path": "/myapp/prod"}],
    )
    client = _mock_client(path_values={"/myapp/prod/SECRET_KEY": "abc123"})

    result = sync(config, client=client)

    assert result == {"SECRET_KEY": "abc123"}


def test_sync_raises_sync_error_on_ssm_failure(tmp_path):
    config = _make_config(tmp_path)
    client = MagicMock()
    client.get_parameter.side_effect = SSMError("not found")

    with pytest.raises(SyncError, match="Failed to fetch parameter"):
        sync(config, client=client)


def test_sync_creates_parent_directories(tmp_path):
    nested_env = tmp_path / "nested" / "dir" / ".env"
    config = _make_config(tmp_path, env_file=str(nested_env))
    client = _mock_client(param_values={"/app/DB_URL": "sqlite:///db"})

    sync(config, client=client)

    assert nested_env.exists()
