"""Unit tests for envault.health."""
from __future__ import annotations

import types
import pytest

from envault.health import (
    HealthCheckResult,
    HealthReport,
    check_config_valid,
    check_ssm_connectivity,
    run_health_checks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(ssm_path="/myapp/prod", env_file=".env"):
    cfg = types.SimpleNamespace(ssm_path=ssm_path, env_file=env_file)
    return cfg


class _GoodSSMClient:
    def get_parameters_by_path(self, path):
        return []


class _BadSSMClient:
    def get_parameters_by_path(self, path):
        raise ConnectionError("network unreachable")


# ---------------------------------------------------------------------------
# HealthCheckResult
# ---------------------------------------------------------------------------

def test_result_to_dict_contains_all_keys():
    r = HealthCheckResult(name="foo", ok=True, message="bar", elapsed_ms=12.5)
    d = r.to_dict()
    assert d["name"] == "foo"
    assert d["ok"] is True
    assert d["message"] == "bar"
    assert d["elapsed_ms"] == 12.5


# ---------------------------------------------------------------------------
# HealthReport
# ---------------------------------------------------------------------------

def test_report_healthy_when_all_ok():
    report = HealthReport(checks=[
        HealthCheckResult("a", True, "ok"),
        HealthCheckResult("b", True, "ok"),
    ])
    assert report.healthy is True


def test_report_unhealthy_when_any_fail():
    report = HealthReport(checks=[
        HealthCheckResult("a", True, "ok"),
        HealthCheckResult("b", False, "boom"),
    ])
    assert report.healthy is False


def test_report_summary_contains_status_labels():
    report = HealthReport(checks=[
        HealthCheckResult("ssm", True, "reachable"),
        HealthCheckResult("cfg", False, "missing ssm_path"),
    ])
    summary = report.summary()
    assert "[OK]" in summary
    assert "[FAIL]" in summary
    assert "unhealthy" in summary


def test_report_to_dict_structure():
    report = HealthReport(checks=[HealthCheckResult("x", True, "ok")])
    d = report.to_dict()
    assert "healthy" in d
    assert "checks" in d
    assert len(d["checks"]) == 1


# ---------------------------------------------------------------------------
# check_config_valid
# ---------------------------------------------------------------------------

def test_check_config_valid_ok():
    result = check_config_valid(_make_config())
    assert result.ok is True
    assert "ssm_path" in result.message


def test_check_config_valid_missing_ssm_path():
    result = check_config_valid(_make_config(ssm_path=""))
    assert result.ok is False
    assert "ssm_path" in result.message


def test_check_config_valid_missing_env_file():
    result = check_config_valid(_make_config(env_file=""))
    assert result.ok is False
    assert "env_file" in result.message


# ---------------------------------------------------------------------------
# check_ssm_connectivity
# ---------------------------------------------------------------------------

def test_check_ssm_connectivity_success():
    result = check_ssm_connectivity(_GoodSSMClient(), "/myapp")
    assert result.ok is True
    assert result.elapsed_ms >= 0


def test_check_ssm_connectivity_failure():
    result = check_ssm_connectivity(_BadSSMClient(), "/myapp")
    assert result.ok is False
    assert "network unreachable" in result.message


# ---------------------------------------------------------------------------
# run_health_checks
# ---------------------------------------------------------------------------

def test_run_health_checks_returns_report():
    report = run_health_checks(_make_config(), _GoodSSMClient())
    assert isinstance(report, HealthReport)
    assert len(report.checks) == 2


def test_run_health_checks_all_pass():
    report = run_health_checks(_make_config(), _GoodSSMClient())
    assert report.healthy is True


def test_run_health_checks_fails_on_bad_ssm():
    report = run_health_checks(_make_config(), _BadSSMClient())
    assert report.healthy is False
