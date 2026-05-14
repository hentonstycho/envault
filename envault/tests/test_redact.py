"""Tests for envault.redact."""

from __future__ import annotations

import pytest

from envault.redact import (
    is_sensitive,
    mask_value,
    redact_env_map,
    redact_string,
)


# ---------------------------------------------------------------------------
# is_sensitive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", [
    "PASSWORD", "db_password", "API_KEY", "api-key",
    "SECRET", "AUTH_TOKEN", "private_key", "PASSWD",
])
def test_is_sensitive_returns_true_for_known_patterns(key: str) -> None:
    assert is_sensitive(key) is True


@pytest.mark.parametrize("key", [
    "DATABASE_URL", "APP_ENV", "PORT", "LOG_LEVEL",
])
def test_is_sensitive_returns_false_for_benign_keys(key: str) -> None:
    assert is_sensitive(key) is False


# ---------------------------------------------------------------------------
# mask_value
# ---------------------------------------------------------------------------

def test_mask_value_returns_mask() -> None:
    assert mask_value("supersecret") == "********"


def test_mask_value_empty_string() -> None:
    assert mask_value("") == "********"


def test_mask_value_partial_shows_suffix() -> None:
    result = mask_value("supersecretABCD", partial=True)
    assert result.endswith("ABCD")
    assert result.startswith("********")


def test_mask_value_partial_short_value_fully_masked() -> None:
    # Value too short to reveal a suffix
    result = mask_value("hi", partial=True)
    assert result == "********"


# ---------------------------------------------------------------------------
# redact_env_map
# ---------------------------------------------------------------------------

def test_redact_env_map_masks_sensitive_keys() -> None:
    env = {"API_KEY": "abc123", "APP_ENV": "production"}
    result = redact_env_map(env)
    assert result["API_KEY"] == "********"
    assert result["APP_ENV"] == "production"


def test_redact_env_map_extra_keys_are_masked() -> None:
    env = {"MY_CUSTOM_KEY": "topsecret", "PORT": "8080"}
    result = redact_env_map(env, extra_keys=["MY_CUSTOM_KEY"])
    assert result["MY_CUSTOM_KEY"] == "********"
    assert result["PORT"] == "8080"


def test_redact_env_map_does_not_mutate_original() -> None:
    env = {"PASSWORD": "hunter2"}
    redact_env_map(env)
    assert env["PASSWORD"] == "hunter2"


def test_redact_env_map_partial_flag_propagated() -> None:
    env = {"SECRET_TOKEN": "abcdefghijklmnop"}
    result = redact_env_map(env, partial=True)
    assert result["SECRET_TOKEN"].endswith("mnop")


# ---------------------------------------------------------------------------
# redact_string
# ---------------------------------------------------------------------------

def test_redact_string_replaces_secrets() -> None:
    text = "connecting with password=hunter2 to host"
    result = redact_string(text, ["hunter2"])
    assert "hunter2" not in result
    assert "********" in result


def test_redact_string_ignores_empty_secrets() -> None:
    text = "some log line"
    result = redact_string(text, ["", "   "])
    assert result == text


def test_redact_string_multiple_secrets() -> None:
    text = "token=abc123 and key=xyz789"
    result = redact_string(text, ["abc123", "xyz789"])
    assert "abc123" not in result
    assert "xyz789" not in result
