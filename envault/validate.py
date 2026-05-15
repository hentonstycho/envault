"""Validate synced environment variables against expected schema."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ValidationError(Exception):
    """Raised when validation cannot be performed."""


@dataclass
class RuleViolation:
    key: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.key}: [{self.rule}] {self.message}"


@dataclass
class ValidationResult:
    violations: List[RuleViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0

    def summary(self) -> str:
        if self.ok:
            return "All variables passed validation."
        lines = [f"{len(self.violations)} violation(s) found:"]
        lines.extend(f"  - {v}" for v in self.violations)
        return "\n".join(lines)


def _check_required(key: str, env_map: Dict[str, str]) -> Optional[RuleViolation]:
    if key not in env_map or env_map[key].strip() == "":
        return RuleViolation(key, "required", "key is missing or empty")
    return None


def _check_pattern(
    key: str, value: str, pattern: str
) -> Optional[RuleViolation]:
    try:
        if not re.fullmatch(pattern, value):
            return RuleViolation(
                key, "pattern", f"value does not match pattern '{pattern}'"
            )
    except re.error as exc:
        raise ValidationError(f"Invalid regex for key '{key}': {exc}") from exc
    return None


def validate(
    env_map: Dict[str, str],
    rules: Dict[str, Dict],
) -> ValidationResult:
    """Validate *env_map* against *rules*.

    Each rule entry may contain:
      required (bool)   – key must be present and non-empty
      pattern  (str)    – value must match this regex
    """
    result = ValidationResult()
    for key, rule in rules.items():
        if rule.get("required", False):
            v = _check_required(key, env_map)
            if v:
                result.violations.append(v)
                continue  # no point checking pattern on missing key

        if "pattern" in rule and key in env_map:
            v = _check_pattern(key, env_map[key], rule["pattern"])
            if v:
                result.violations.append(v)

    return result
