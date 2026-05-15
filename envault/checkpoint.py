"""Checkpoint tracking: record the last successful sync time per profile."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class CheckpointError(Exception):
    """Raised when checkpoint file is corrupt or unreadable."""


@dataclass
class Checkpoint:
    """Persisted record of the last successful sync for a profile."""

    profile: str
    synced_at: float  # Unix timestamp
    env_file: str
    param_count: int
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "synced_at": self.synced_at,
            "env_file": self.env_file,
            "param_count": self.param_count,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            profile=data["profile"],
            synced_at=float(data["synced_at"]),
            env_file=data["env_file"],
            param_count=int(data["param_count"]),
            extra=data.get("extra", {}),
        )

    def age_seconds(self, now: Optional[float] = None) -> float:
        """Return how many seconds have elapsed since this checkpoint."""
        return (now if now is not None else time.time()) - self.synced_at


def _checkpoint_path(directory: Path, profile: str) -> Path:
    safe = profile.replace("/", "_").strip("_") or "default"
    return directory / f".envault_checkpoint_{safe}.json"


def save_checkpoint(directory: Path, checkpoint: Checkpoint) -> None:
    """Write a checkpoint to *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    path = _checkpoint_path(directory, checkpoint.profile)
    path.write_text(json.dumps(checkpoint.to_dict(), indent=2), encoding="utf-8")


def load_checkpoint(directory: Path, profile: str) -> Optional[Checkpoint]:
    """Return the stored checkpoint or *None* if it does not exist."""
    path = _checkpoint_path(directory, profile)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Checkpoint.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CheckpointError(f"Corrupt checkpoint file {path}: {exc}") from exc


def clear_checkpoint(directory: Path, profile: str) -> bool:
    """Delete the checkpoint file for *profile*. Returns True if it existed."""
    path = _checkpoint_path(directory, profile)
    if path.exists():
        path.unlink()
        return True
    return False
