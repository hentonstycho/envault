"""Tests for envault.export."""
from __future__ import annotations

import pytest
from pathlib import Path

from envault.export import (
    ExportFormat,
    ExportError,
    export_env,
    _escape_value,
)


# ---------------------------------------------------------------------------
# _escape_value
# ---------------------------------------------------------------------------

def test_escape_posix_simple():
    assert _escape_value("hello", ExportFormat.POSIX) == "'hello'"


def test_escape_posix_with_single_quote():
    result = _escape_value("it's", ExportFormat.POSIX)
    assert result == "'it'\\''s'"


def test_escape_dotenv_with_double_quote():
    result = _escape_value('say "hi"', ExportFormat.DOTENV)
    assert result == '"say \\"hi\\""'


def test_escape_fish_with_single_quote():
    result = _escape_value("it's", ExportFormat.FISH)
    assert "'" in result


# ---------------------------------------------------------------------------
# export_env — rendered output
# ---------------------------------------------------------------------------

ENV = {"DB_HOST": "localhost", "API_KEY": "s3cr3t"}


def test_export_dotenv_format():
    out = export_env(ENV, ExportFormat.DOTENV)
    assert 'DB_HOST="localhost"' in out
    assert 'API_KEY="s3cr3t"' in out


def test_export_posix_format():
    out = export_env(ENV, ExportFormat.POSIX)
    assert out.startswith("#!/usr/bin/env sh")
    assert "export DB_HOST='localhost'" in out
    assert "export API_KEY='s3cr3t'" in out


def test_export_fish_format():
    out = export_env(ENV, ExportFormat.FISH)
    assert out.startswith("#!/usr/bin/env fish")
    assert "set -x DB_HOST" in out


def test_export_keys_sorted():
    env = {"Z_KEY": "z", "A_KEY": "a"}
    out = export_env(env, ExportFormat.DOTENV)
    assert out.index("A_KEY") < out.index("Z_KEY")


def test_export_empty_env():
    out = export_env({}, ExportFormat.DOTENV)
    assert out.strip() == ""


# ---------------------------------------------------------------------------
# export_env — file writing
# ---------------------------------------------------------------------------

def test_export_writes_file(tmp_path: Path):
    dest = tmp_path / "out" / "vars.env"
    result = export_env(ENV, ExportFormat.DOTENV, output_path=dest)
    assert dest.exists()
    assert dest.read_text() == result


def test_export_returns_string_without_path():
    result = export_env(ENV, ExportFormat.POSIX)
    assert isinstance(result, str)
    assert len(result) > 0


def test_export_write_error_raises(tmp_path: Path):
    # Make the target path a directory so write_text fails
    bad_path = tmp_path / "dir_not_file"
    bad_path.mkdir()
    with pytest.raises(ExportError):
        export_env(ENV, ExportFormat.DOTENV, output_path=bad_path)
