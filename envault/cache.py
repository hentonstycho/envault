"""Local parameter cache to reduce SSM API calls during sync."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

DEFAULT_TTL = 300  # seconds
CACHE_FILENAME = ".envault_cache.json"


@dataclass
class CacheEntry:
    value: str
    fetched_at: float
    ttl: int = DEFAULT_TTL

    def is_expired(self) -> bool:
        return (time.time() - self.fetched_at) > self.ttl

    def to_dict(self) -> dict:
        return {"value": self.value, "fetched_at": self.fetched_at, "ttl": self.ttl}

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(
            value=data["value"],
            fetched_at=float(data["fetched_at"]),
            ttl=int(data.get("ttl", DEFAULT_TTL)),
        )


@dataclass
class ParameterCache:
    cache_dir: Path
    ttl: int = DEFAULT_TTL
    _entries: Dict[str, CacheEntry] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._path = self.cache_dir / CACHE_FILENAME
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            self._entries = {k: CacheEntry.from_dict(v) for k, v in raw.items()}
        except (json.JSONDecodeError, KeyError):
            self._entries = {}

    def _save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
        )

    def get(self, key: str) -> Optional[str]:
        entry = self._entries.get(key)
        if entry is None or entry.is_expired():
            return None
        return entry.value

    def set(self, key: str, value: str) -> None:
        self._entries[key] = CacheEntry(
            value=value, fetched_at=time.time(), ttl=self.ttl
        )
        self._save()

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)
        self._save()

    def clear(self) -> None:
        self._entries = {}
        if self._path.exists():
            self._path.unlink()
