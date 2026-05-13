"""Audit log support: record sync events to a local JSONL file."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

DEFAULT_AUDIT_FILE = ".envault-audit.jsonl"


@dataclass
class AuditEntry:
    event: str  # "sync", "check", "error"
    profile: str
    env_file: str
    keys_written: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "profile": self.profile,
            "env_file": self.env_file,
            "keys_written": self.keys_written,
            "error": self.error,
        }


def append_entry(entry: AuditEntry, audit_file: Path = Path(DEFAULT_AUDIT_FILE)) -> None:
    """Append a single audit entry as a JSON line."""
    try:
        with audit_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
        log.debug("Audit entry written to %s", audit_file)
    except OSError as exc:
        log.warning("Could not write audit log: %s", exc)


def read_entries(audit_file: Path = Path(DEFAULT_AUDIT_FILE)) -> List[AuditEntry]:
    """Read all audit entries from a JSONL file."""
    if not audit_file.exists():
        return []
    entries: List[AuditEntry] = []
    with audit_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            entries.append(
                AuditEntry(
                    event=data["event"],
                    profile=data["profile"],
                    env_file=data["env_file"],
                    keys_written=data.get("keys_written", []),
                    error=data.get("error"),
                    timestamp=data["timestamp"],
                )
            )
    return entries
