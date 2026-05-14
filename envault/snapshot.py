"""Snapshot management for envault — capture and compare .env state over time."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


SNAPSHOT_DIR = Path(".envault") / "snapshots"


class SnapshotError(Exception):
    """Raised when snapshot operations fail."""


@dataclass
class Snapshot:
    """A point-in-time capture of resolved SSM parameter values."""

    timestamp: float
    profile: str
    checksum: str
    keys: List[str]
    values: Dict[str, str] = field(repr=False)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "profile": self.profile,
            "checksum": self.checksum,
            "keys": self.keys,
            "values": self.values,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        return cls(
            timestamp=data["timestamp"],
            profile=data["profile"],
            checksum=data["checksum"],
            keys=data["keys"],
            values=data["values"],
        )


def _checksum(values: Dict[str, str]) -> str:
    """Compute a stable SHA-256 checksum over sorted key=value pairs."""
    payload = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    return hashlib.sha256(payload.encode()).hexdigest()


def save_snapshot(profile: str, values: Dict[str, str], snapshot_dir: Path = SNAPSHOT_DIR) -> Snapshot:
    """Persist a snapshot for the given profile and return it."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap = Snapshot(
        timestamp=time.time(),
        profile=profile,
        checksum=_checksum(values),
        keys=sorted(values.keys()),
        values=values,
    )
    path = snapshot_dir / f"{profile}.json"
    path.write_text(json.dumps(snap.to_dict(), indent=2))
    return snap


def load_snapshot(profile: str, snapshot_dir: Path = SNAPSHOT_DIR) -> Optional[Snapshot]:
    """Load the most recent snapshot for *profile*, or None if absent."""
    path = snapshot_dir / f"{profile}.json"
    if not path.exists():
        return None
    try:
        return Snapshot.from_dict(json.loads(path.read_text()))
    except (KeyError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Corrupt snapshot for profile '{profile}': {exc}") from exc


def snapshots_match(a: Snapshot, b: Snapshot) -> bool:
    """Return True when two snapshots have identical checksums."""
    return a.checksum == b.checksum
