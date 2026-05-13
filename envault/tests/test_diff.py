"""Tests for envault.diff module."""
from __future__ import annotations

from pathlib import Path

import pytest

from envault.diff import DiffResult, compute_diff, parse_env_file


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    return tmp_path / ".env"


def test_parse_env_file_basic(env_file: Path) -> None:
    env_file.write_text('FOO=bar\nBAZ=qux\n')
    result = parse_env_file(env_file)
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_file_ignores_comments(env_file: Path) -> None:
    env_file.write_text('# comment\nFOO=bar\n\nBAZ=qux\n')
    result = parse_env_file(env_file)
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_file_strips_quotes(env_file: Path) -> None:
    env_file.write_text('FOO="hello world"\nBAR=\'single\'\n')
    result = parse_env_file(env_file)
    assert result["FOO"] == "hello world"
    assert result["BAR"] == "single"


def test_parse_env_file_missing_returns_empty(tmp_path: Path) -> None:
    result = parse_env_file(tmp_path / "nonexistent.env")
    assert result == {}


def test_compute_diff_added() -> None:
    diff = compute_diff(local={}, remote={"NEW_KEY": "value"})
    assert "NEW_KEY" in diff.added
    assert diff.has_changes


def test_compute_diff_removed() -> None:
    diff = compute_diff(local={"OLD_KEY": "v"}, remote={})
    assert "OLD_KEY" in diff.removed
    assert diff.has_changes


def test_compute_diff_changed() -> None:
    diff = compute_diff(local={"KEY": "old"}, remote={"KEY": "new"})
    assert "KEY" in diff.changed
    assert diff.changed["KEY"] == ("old", "new")
    assert diff.has_changes


def test_compute_diff_unchanged() -> None:
    diff = compute_diff(local={"KEY": "same"}, remote={"KEY": "same"})
    assert "KEY" in diff.unchanged
    assert not diff.has_changes


def test_diff_result_summary_no_changes() -> None:
    diff = DiffResult()
    assert diff.summary() == "No changes"


def test_diff_result_summary_with_changes() -> None:
    diff = DiffResult(
        added={"A": "1"},
        changed={"B": ("old", "new")},
        removed=["C"],
    )
    summary = diff.summary()
    assert "+1 added" in summary
    assert "~1 changed" in summary
    assert "-1 removed" in summary
