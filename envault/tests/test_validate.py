"""Tests for envault.validate."""
import pytest

from envault.validate import (
    ValidationError,
    ValidationResult,
    validate,
    _check_required,
    _check_pattern,
)


# ---------------------------------------------------------------------------
# _check_required
# ---------------------------------------------------------------------------

def test_check_required_present_and_nonempty():
    assert _check_required("FOO", {"FOO": "bar"}) is None


def test_check_required_missing_key():
    v = _check_required("FOO", {})
    assert v is not None
    assert v.key == "FOO"
    assert v.rule == "required"


def test_check_required_empty_value():
    v = _check_required("FOO", {"FOO": "   "})
    assert v is not None
    assert "empty" in v.message


# ---------------------------------------------------------------------------
# _check_pattern
# ---------------------------------------------------------------------------

def test_check_pattern_matches():
    assert _check_pattern("PORT", "8080", r"\d+") is None


def test_check_pattern_no_match():
    v = _check_pattern("PORT", "abc", r"\d+")
    assert v is not None
    assert v.rule == "pattern"
    assert "\\d+" in v.message


def test_check_pattern_invalid_regex_raises():
    with pytest.raises(ValidationError, match="Invalid regex"):
        _check_pattern("KEY", "value", "[invalid")


# ---------------------------------------------------------------------------
# validate — full integration
# ---------------------------------------------------------------------------

def test_validate_all_pass():
    env_map = {"DATABASE_URL": "postgres://localhost/db", "PORT": "5432"}
    rules = {
        "DATABASE_URL": {"required": True},
        "PORT": {"required": True, "pattern": r"\d+"},
    }
    result = validate(env_map, rules)
    assert result.ok
    assert "passed" in result.summary()


def test_validate_missing_required_key():
    result = validate({}, {"SECRET_KEY": {"required": True}})
    assert not result.ok
    assert any(v.key == "SECRET_KEY" for v in result.violations)


def test_validate_pattern_violation():
    env_map = {"PORT": "not-a-number"}
    rules = {"PORT": {"pattern": r"\d+"}}
    result = validate(env_map, rules)
    assert not result.ok
    assert result.violations[0].rule == "pattern"


def test_validate_skips_pattern_when_key_missing():
    """If required fails, pattern check is skipped for the same key."""
    rules = {"PORT": {"required": True, "pattern": r"\d+"}}
    result = validate({}, rules)
    # Only one violation (required), not two
    assert len(result.violations) == 1


def test_validate_empty_rules_always_passes():
    result = validate({"FOO": "bar"}, {})
    assert result.ok


def test_validation_result_summary_lists_violations():
    env_map = {"A": "", "B": "bad"}
    rules = {
        "A": {"required": True},
        "B": {"pattern": r"\d+"},
    }
    result = validate(env_map, rules)
    summary = result.summary()
    assert "2 violation" in summary
    assert "A" in summary
    assert "B" in summary
