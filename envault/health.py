"""Health check module: verifies SSM connectivity and config validity."""
from __future__ import annotations

import dataclasses
import time
from typing import List, Optional


@dataclasses.dataclass
class HealthCheckResult:
    name: str
    ok: bool
    message: str
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


@dataclasses.dataclass
class HealthReport:
    checks: List[HealthCheckResult] = dataclasses.field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return all(c.ok for c in self.checks)

    def summary(self) -> str:
        lines = []
        for c in self.checks:
            status = "OK" if c.ok else "FAIL"
            lines.append(f"[{status}] {c.name}: {c.message} ({c.elapsed_ms:.1f}ms)")
        overall = "healthy" if self.healthy else "unhealthy"
        lines.append(f"Overall: {overall}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "checks": [c.to_dict() for c in self.checks],
        }


def _timed(fn) -> tuple[bool, str, float]:
    """Run fn(); return (ok, message, elapsed_ms)."""
    start = time.monotonic()
    try:
        msg = fn()
        elapsed = (time.monotonic() - start) * 1000
        return True, msg or "ok", elapsed
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.monotonic() - start) * 1000
        return False, str(exc), elapsed


def check_ssm_connectivity(ssm_client, path: str) -> HealthCheckResult:
    """Attempt a lightweight SSM describe call to verify credentials/network."""
    def _probe():
        # get_parameters_by_path with max_results=1 is a cheap probe
        ssm_client.get_parameters_by_path(path)
        return "SSM reachable"

    ok, msg, elapsed = _timed(_probe)
    return HealthCheckResult(name="ssm_connectivity", ok=ok, message=msg, elapsed_ms=elapsed)


def check_config_valid(config) -> HealthCheckResult:
    """Verify the loaded config has required fields populated."""
    def _probe():
        missing = []
        if not getattr(config, "ssm_path", None):
            missing.append("ssm_path")
        if not getattr(config, "env_file", None):
            missing.append("env_file")
        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")
        return f"config ok (ssm_path={config.ssm_path})"

    ok, msg, elapsed = _timed(_probe)
    return HealthCheckResult(name="config_valid", ok=ok, message=msg, elapsed_ms=elapsed)


def run_health_checks(config, ssm_client) -> HealthReport:
    report = HealthReport()
    report.checks.append(check_config_valid(config))
    report.checks.append(check_ssm_connectivity(ssm_client, getattr(config, "ssm_path", "/")))
    return report
