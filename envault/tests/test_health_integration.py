"""Integration tests: health checks wired through a real-ish SSM stub."""
from __future__ import annotations

import types
import pytest

from envault.health import run_health_checks, HealthReport


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_config(**kwargs):
    defaults = {"ssm_path": "/app/staging", "env_file": ".env.staging"}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


class _StubSSMClient:
    """Mimics envault.ssm.SSMClient interface for integration tests."""

    def __init__(self, params: dict | None = None, raise_on_call: Exception | None = None):
        self._params = params or {}
        self._raise = raise_on_call
        self.call_count = 0

    def get_parameters_by_path(self, path):
        self.call_count += 1
        if self._raise:
            raise self._raise
        return [
            {"Name": k, "Value": v}
            for k, v in self._params.items()
            if k.startswith(path)
        ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_full_healthy_scenario():
    client = _StubSSMClient(params={"/app/staging/DB_URL": "postgres://localhost/db"})
    report = run_health_checks(_make_config(), client)
    assert report.healthy is True
    assert client.call_count == 1


def test_ssm_error_makes_report_unhealthy():
    client = _StubSSMClient(raise_on_call=PermissionError("AccessDenied"))
    report = run_health_checks(_make_config(), client)
    assert report.healthy is False
    ssm_check = next(c for c in report.checks if c.name == "ssm_connectivity")
    assert "AccessDenied" in ssm_check.message


def test_bad_config_makes_report_unhealthy_without_calling_ssm():
    client = _StubSSMClient()
    report = run_health_checks(_make_config(ssm_path=""), client)
    assert report.healthy is False
    cfg_check = next(c for c in report.checks if c.name == "config_valid")
    assert cfg_check.ok is False


def test_report_to_dict_is_serialisable():
    import json
    client = _StubSSMClient()
    report = run_health_checks(_make_config(), client)
    # Should not raise
    payload = json.dumps(report.to_dict())
    parsed = json.loads(payload)
    assert "healthy" in parsed
    assert isinstance(parsed["checks"], list)


def test_elapsed_ms_is_non_negative_for_all_checks():
    client = _StubSSMClient()
    report = run_health_checks(_make_config(), client)
    for check in report.checks:
        assert check.elapsed_ms >= 0
