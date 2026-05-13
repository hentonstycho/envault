"""Parameter rotation helpers — detect stale secrets and prompt re-sync."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from envault.audit import read_entries


@dataclass
class RotationStatus:
    """Staleness report for a single parameter path."""

    path: str
    last_synced: Optional[datetime.datetime]
    age_days: Optional[float]
    is_stale: bool
    threshold_days: int

    def summary(self) -> str:
        if self.last_synced is None:
            return f"{self.path}: never synced"
        age = f"{self.age_days:.1f}d"
        flag = " [STALE]" if self.is_stale else ""
        return f"{self.path}: last synced {age} ago{flag}"


@dataclass
class RotationReport:
    statuses: List[RotationStatus] = field(default_factory=list)

    @property
    def stale_paths(self) -> List[str]:
        return [s.path for s in self.statuses if s.is_stale]

    @property
    def has_stale(self) -> bool:
        return bool(self.stale_paths)


def _last_sync_time(
    path: str, audit_file: str
) -> Optional[datetime.datetime]:
    """Return the most recent sync timestamp for *path* from the audit log."""
    entries = read_entries(audit_file)
    matches = [
        e for e in entries if e.get("path") == path and e.get("action") == "sync"
    ]
    if not matches:
        return None
    latest = max(matches, key=lambda e: e.get("timestamp", ""))
    ts = latest.get("timestamp", "")
    try:
        return datetime.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def check_rotation(
    paths: List[str],
    audit_file: str,
    threshold_days: int = 30,
) -> RotationReport:
    """Build a :class:`RotationReport` for every path in *paths*."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    report = RotationReport()
    for path in paths:
        last = _last_sync_time(path, audit_file)
        if last is None:
            age = None
            stale = True
        else:
            if last.tzinfo is None:
                last = last.replace(tzinfo=datetime.timezone.utc)
            age = (now - last).total_seconds() / 86400
            stale = age > threshold_days
        report.statuses.append(
            RotationStatus(
                path=path,
                last_synced=last,
                age_days=age,
                is_stale=stale,
                threshold_days=threshold_days,
            )
        )
    return report
