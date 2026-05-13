"""Tests for envault.audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from envault.audit import AuditEntry, append_entry, read_entries


@pytest.fixture()
def audit_file(tmp_path: Path) -> Path:
    return tmp_path / "test-audit.jsonl"


def _make_entry(**kwargs) -> AuditEntry:
    defaults = dict(
        event="sync",
        profile="default",
        env_file=".env",
        keys_written=["DB_URL", "API_KEY"],
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


def test_append_creates_file(audit_file: Path) -> None:
    entry = _make_entry()
    append_entry(entry, audit_file)
    assert audit_file.exists()


def test_append_writes_valid_json(audit_file: Path) -> None:
    entry = _make_entry()
    append_entry(entry, audit_file)
    raw = audit_file.read_text(encoding="utf-8").strip()
    data = json.loads(raw)
    assert data["event"] == "sync"
    assert data["profile"] == "default"
    assert data["keys_written"] == ["DB_URL", "API_KEY"]
    assert data["error"] is None
    assert "timestamp" in data


def test_append_multiple_entries(audit_file: Path) -> None:
    append_entry(_make_entry(event="sync"), audit_file)
    append_entry(_make_entry(event="check"), audit_file)
    lines = [l for l in audit_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_read_entries_empty_when_no_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.jsonl"
    assert read_entries(missing) == []


def test_read_entries_roundtrip(audit_file: Path) -> None:
    entry = _make_entry(event="error", error="SSMError: not found")
    append_entry(entry, audit_file)
    results = read_entries(audit_file)
    assert len(results) == 1
    assert results[0].event == "error"
    assert results[0].error == "SSMError: not found"
    assert results[0].keys_written == ["DB_URL", "API_KEY"]


def test_append_does_not_raise_on_bad_path(tmp_path: Path, caplog) -> None:
    """A non-writable path should log a warning, not crash."""
    bad_path = tmp_path / "no_dir" / "audit.jsonl"
    entry = _make_entry()
    # Should not raise
    append_entry(entry, bad_path)
