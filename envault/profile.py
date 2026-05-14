"""Profile support — load named environment profiles from envault.toml.

Allows users to define multiple named profiles (e.g. dev, staging, prod)
each with their own SSM path prefix and output .env file target.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import tomllib


class ProfileError(Exception):
    """Raised when profile loading or resolution fails."""


@dataclass
class Profile:
    name: str
    path_prefix: str
    output: str
    region: Optional[str] = None
    recursive: bool = True
    extra_tags: Dict[str, str] = field(default_factory=dict)

    def output_path(self, base_dir: Path) -> Path:
        return base_dir / self.output


def load_profiles(config_path: Path) -> Dict[str, Profile]:
    """Parse [profiles.<name>] sections from an envault.toml file.

    Returns a dict mapping profile name -> Profile.
    Raises ProfileError if the file is missing or malformed.
    """
    if not config_path.exists():
        raise ProfileError(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"Invalid TOML in {config_path}: {exc}") from exc

    raw_profiles: Dict[str, dict] = data.get("profiles", {})
    if not raw_profiles:
        return {}

    profiles: Dict[str, Profile] = {}
    for name, cfg in raw_profiles.items():
        if "path_prefix" not in cfg:
            raise ProfileError(f"Profile '{name}' is missing required key 'path_prefix'")
        if "output" not in cfg:
            raise ProfileError(f"Profile '{name}' is missing required key 'output'")
        profiles[name] = Profile(
            name=name,
            path_prefix=cfg["path_prefix"],
            output=cfg["output"],
            region=cfg.get("region"),
            recursive=cfg.get("recursive", True),
            extra_tags=cfg.get("extra_tags", {}),
        )
    return profiles


def resolve_profile(profiles: Dict[str, Profile], name: str) -> Profile:
    """Return the named profile or raise ProfileError."""
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none defined)"
        raise ProfileError(
            f"Unknown profile '{name}'. Available profiles: {available}"
        )
    return profiles[name]


def list_profile_names(profiles: Dict[str, Profile]) -> List[str]:
    return sorted(profiles.keys())
