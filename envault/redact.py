"""Utilities for redacting sensitive values in logs and output."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Optional

# Keys whose values should always be fully masked
_ALWAYS_MASK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|auth)", re.I),
]

_MASK = "********"
_PARTIAL_VISIBLE = 4  # chars to show at end for partial reveal


def is_sensitive(key: str) -> bool:
    """Return True if *key* looks like it holds a sensitive value."""
    return any(p.search(key) for p in _ALWAYS_MASK_PATTERNS)


def mask_value(value: str, *, partial: bool = False) -> str:
    """Return a masked representation of *value*.

    If *partial* is True and the value is long enough, show the last few
    characters so users can verify rotation without exposing the full secret.
    """
    if not value:
        return _MASK
    if partial and len(value) > _PARTIAL_VISIBLE + 2:
        return _MASK + value[-_PARTIAL_VISIBLE:]
    return _MASK


def redact_env_map(
    env: Dict[str, str],
    *,
    extra_keys: Optional[Iterable[str]] = None,
    partial: bool = False,
) -> Dict[str, str]:
    """Return a copy of *env* with sensitive values replaced by masks.

    Parameters
    ----------
    env:
        Mapping of environment variable names to their plaintext values.
    extra_keys:
        Additional key names that should be treated as sensitive regardless
        of their name pattern.
    partial:
        When True, masked values include a short suffix for identification.
    """
    sensitive: set[str] = set(extra_keys or [])
    result: Dict[str, str] = {}
    for key, value in env.items():
        if key in sensitive or is_sensitive(key):
            result[key] = mask_value(value, partial=partial)
        else:
            result[key] = value
    return result


def redact_string(text: str, secrets: Iterable[str]) -> str:
    """Replace every occurrence of each secret in *text* with the mask.

    Useful for sanitising log lines that may have accidentally captured a
    raw secret value.
    """
    for secret in secrets:
        if secret:
            text = text.replace(secret, _MASK)
    return text
