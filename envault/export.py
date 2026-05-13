"""Export environment variables to shell-sourceable formats."""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class ExportFormat(str, Enum):
    DOTENV = "dotenv"
    POSIX = "posix"
    FISH = "fish"


class ExportError(Exception):
    """Raised when export fails."""


def _escape_value(value: str, fmt: ExportFormat) -> str:
    """Escape a value appropriately for the target shell format."""
    if fmt == ExportFormat.POSIX:
        escaped = value.replace("'", "'\\''")
        return f"'{escaped}'"
    if fmt == ExportFormat.FISH:
        escaped = value.replace("'", "\\'")
        return f"'{escaped}'"
    # dotenv: wrap in double quotes, escape inner double quotes
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _render_posix(env: Dict[str, str]) -> str:
    lines = ["#!/usr/bin/env sh"]
    for key, value in sorted(env.items()):
        lines.append(f"export {key}={_escape_value(value, ExportFormat.POSIX)}")
    return "\n".join(lines) + "\n"


def _render_fish(env: Dict[str, str]) -> str:
    lines = ["#!/usr/bin/env fish"]
    for key, value in sorted(env.items()):
        lines.append(f"set -x {key} {_escape_value(value, ExportFormat.FISH)}")
    return "\n".join(lines) + "\n"


def _render_dotenv(env: Dict[str, str]) -> str:
    lines: list[str] = []
    for key, value in sorted(env.items()):
        lines.append(f"{key}={_escape_value(value, ExportFormat.DOTENV)}")
    return "\n".join(lines) + "\n"


_RENDERERS = {
    ExportFormat.POSIX: _render_posix,
    ExportFormat.FISH: _render_fish,
    ExportFormat.DOTENV: _render_dotenv,
}


def export_env(
    env: Dict[str, str],
    fmt: ExportFormat = ExportFormat.DOTENV,
    output_path: Optional[Path] = None,
) -> str:
    """Render *env* in *fmt* and optionally write to *output_path*.

    Returns the rendered string in all cases.
    """
    renderer = _RENDERERS.get(fmt)
    if renderer is None:  # pragma: no cover
        raise ExportError(f"Unknown export format: {fmt}")

    rendered = renderer(env)

    if output_path is not None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            raise ExportError(f"Failed to write export file: {exc}") from exc

    return rendered
