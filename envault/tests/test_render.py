"""Tests for envault.render module."""
from __future__ import annotations

import io

from envault.diff import DiffResult
from envault.render import render_diff


def _capture(diff: DiffResult, mask_values: bool = True) -> str:
    buf = io.StringIO()
    render_diff(diff, stream=buf, mask_values=mask_values)
    return buf.getvalue()


def test_render_no_changes() -> None:
    diff = DiffResult()
    output = _capture(diff)
    assert "No changes" in output


def test_render_added_key_masked() -> None:
    diff = DiffResult(added={"SECRET": "s3cr3t"})
    output = _capture(diff, mask_values=True)
    assert "+ SECRET" in output
    assert "s3cr3t" not in output
    assert "***" in output


def test_render_added_key_unmasked() -> None:
    diff = DiffResult(added={"SECRET": "s3cr3t"})
    output = _capture(diff, mask_values=False)
    assert "s3cr3t" in output


def test_render_changed_key() -> None:
    diff = DiffResult(changed={"DB_HOST": ("localhost", "prod.db")})
    output = _capture(diff, mask_values=False)
    assert "~ DB_HOST" in output
    assert "localhost" in output
    assert "prod.db" in output


def test_render_removed_key() -> None:
    diff = DiffResult(removed=["OLD_VAR"])
    output = _capture(diff)
    assert "- OLD_VAR" in output


def test_render_summary_line() -> None:
    diff = DiffResult(added={"A": "1"}, removed=["B"])
    output = _capture(diff)
    assert "+1 added" in output
    assert "-1 removed" in output


def test_render_multiple_keys_sorted() -> None:
    diff = DiffResult(added={"Z_KEY": "z", "A_KEY": "a"})
    output = _capture(diff)
    idx_a = output.index("A_KEY")
    idx_z = output.index("Z_KEY")
    assert idx_a < idx_z
