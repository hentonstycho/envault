"""Diff utilities for comparing existing .env files against SSM parameters."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class DiffResult:
    """Represents the difference between a local .env file and SSM parameters."""

    added: Dict[str, str] = field(default_factory=dict)
    changed: Dict[str, tuple] = field(default_factory=dict)  # key -> (old, new)
    removed: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.changed:
            parts.append(f"~{len(self.changed)} changed")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if not parts:
            return "No changes"
        return ", ".join(parts)


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a .env file into a key->value mapping, ignoring comments and blanks."""
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def compute_diff(local: Dict[str, str], remote: Dict[str, str]) -> DiffResult:
    """Compute the diff between local env vars and remote SSM values."""
    result = DiffResult()
    all_keys = set(local) | set(remote)
    for key in sorted(all_keys):
        if key in remote and key not in local:
            result.added[key] = remote[key]
        elif key in local and key not in remote:
            result.removed.append(key)
        elif local[key] != remote[key]:
            result.changed[key] = (local[key], remote[key])
        else:
            result.unchanged.append(key)
    return result
