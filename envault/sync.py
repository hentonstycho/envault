"""Sync SSM parameters to a local .env file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from envault.config import EnvaultConfig
from envault.ssm import SSMClient, SSMError


class SyncError(Exception):
    """Raised when a sync operation fails."""


def _format_env_line(key: str, value: str) -> str:
    """Return a properly quoted KEY=VALUE line."""
    # Wrap value in double-quotes and escape any existing double-quotes.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{key}="{escaped}"'


def _build_env_map(config: EnvaultConfig, client: SSMClient) -> dict[str, str]:
    """Fetch all parameters defined in *config* and return a {env_var: value} map."""
    env_map: dict[str, str] = {}

    # Individual parameters
    for mapping in config.parameters:
        try:
            value = client.get_parameter(mapping["path"])
        except SSMError as exc:
            raise SyncError(f"Failed to fetch parameter '{mapping['path']}": {exc}") from exc
        env_map[mapping["env_var"]] = value

    # Path-based parameters
    for path_cfg in config.paths:
        prefix: str = path_cfg["path"]
        try:
            params = client.get_parameters_by_path(prefix)
        except SSMError as exc:
            raise SyncError(f"Failed to fetch path '{prefix}': {exc}") from exc
        for ssm_name, value in params.items():
            # Derive env var name from the last path segment, uppercased.
            env_var = ssm_name.lstrip("/").split("/")[-1].upper()
            env_map[env_var] = value

    return env_map


def sync(
    config: EnvaultConfig,
    client: Optional[SSMClient] = None,
    *,
    dry_run: bool = False,
) -> dict[str, str]:
    """Sync SSM parameters to the .env file specified in *config*.

    Returns the env map that was (or would be) written.
    Raises :class:`SyncError` on failure.
    """
    if client is None:
        client = SSMClient(region=config.aws_region, profile=config.aws_profile)

    env_map = _build_env_map(config, client)

    if not dry_run:
        output_path = Path(config.env_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [_format_env_line(k, v) for k, v in sorted(env_map.items())]
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return env_map
