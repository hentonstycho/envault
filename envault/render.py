"""Render diff output to the terminal with colour-coded formatting."""
from __future__ import annotations

import sys
from typing import TextIO

from envault.diff import DiffResult

_RESET = "\033[0m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_GREY = "\033[90m"


def _supports_color(stream: TextIO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def _colorize(text: str, color: str, stream: TextIO) -> str:
    if _supports_color(stream):
        return f"{color}{text}{_RESET}"
    return text


def render_diff(diff: DiffResult, stream: TextIO = sys.stdout, *, mask_values: bool = True) -> None:
    """Print a human-readable diff to *stream*."""

    def _val(v: str) -> str:
        if mask_values:
            return "***"
        return v

    if not diff.has_changes:
        print(_colorize("  No changes detected.", _GREY, stream), file=stream)
        return

    for key, value in sorted(diff.added.items()):
        line = f"  + {key}={_val(value)}"
        print(_colorize(line, _GREEN, stream), file=stream)

    for key, (old, new) in sorted(diff.changed.items()):
        line = f"  ~ {key}: {_val(old)} → {_val(new)}"
        print(_colorize(line, _YELLOW, stream), file=stream)

    for key in sorted(diff.removed):
        line = f"  - {key}"
        print(_colorize(line, _RED, stream), file=stream)

    print(file=stream)
    print(f"  {diff.summary()}", file=stream)
