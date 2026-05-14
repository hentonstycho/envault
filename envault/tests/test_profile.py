"""Tests for envault.profile."""
from __future__ import annotations

from pathlib import Path

import pytest

from envault.profile import (
    ProfileError,
    load_profiles,
    resolve_profile,
    list_profile_names,
)


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    return tmp_path / "envault.toml"


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# load_profiles
# ---------------------------------------------------------------------------

def test_load_profiles_returns_empty_when_no_section(config_file):
    _write(config_file, "[sync]\nregion = 'us-east-1'\n")
    assert load_profiles(config_file) == {}


def test_load_profiles_parses_single_profile(config_file):
    _write(config_file, """
[profiles.dev]
path_prefix = "/myapp/dev"
output = ".env.dev"
region = "us-west-2"
""")
    profiles = load_profiles(config_file)
    assert "dev" in profiles
    p = profiles["dev"]
    assert p.path_prefix == "/myapp/dev"
    assert p.output == ".env.dev"
    assert p.region == "us-west-2"
    assert p.recursive is True


def test_load_profiles_parses_multiple_profiles(config_file):
    _write(config_file, """
[profiles.dev]
path_prefix = "/app/dev"
output = ".env.dev"

[profiles.prod]
path_prefix = "/app/prod"
output = ".env.prod"
recursive = false
""")
    profiles = load_profiles(config_file)
    assert set(profiles) == {"dev", "prod"}
    assert profiles["prod"].recursive is False


def test_load_profiles_missing_file_raises(config_file):
    with pytest.raises(ProfileError, match="not found"):
        load_profiles(config_file)


def test_load_profiles_missing_path_prefix_raises(config_file):
    _write(config_file, """
[profiles.bad]
output = ".env"
""")
    with pytest.raises(ProfileError, match="path_prefix"):
        load_profiles(config_file)


def test_load_profiles_missing_output_raises(config_file):
    _write(config_file, """
[profiles.bad]
path_prefix = "/x"
""")
    with pytest.raises(ProfileError, match="output"):
        load_profiles(config_file)


def test_load_profiles_invalid_toml_raises(config_file):
    _write(config_file, "[[[broken")
    with pytest.raises(ProfileError, match="Invalid TOML"):
        load_profiles(config_file)


# ---------------------------------------------------------------------------
# resolve_profile / list_profile_names
# ---------------------------------------------------------------------------

def test_resolve_profile_returns_correct_profile(config_file):
    _write(config_file, """
[profiles.staging]
path_prefix = "/app/staging"
output = ".env.staging"
""")
    profiles = load_profiles(config_file)
    p = resolve_profile(profiles, "staging")
    assert p.name == "staging"


def test_resolve_profile_unknown_raises(config_file):
    _write(config_file, """
[profiles.dev]
path_prefix = "/app/dev"
output = ".env.dev"
""")
    profiles = load_profiles(config_file)
    with pytest.raises(ProfileError, match="Unknown profile 'prod'"):
        resolve_profile(profiles, "prod")


def test_list_profile_names_sorted(config_file):
    _write(config_file, """
[profiles.zebra]
path_prefix = "/z"
output = ".env.z"

[profiles.alpha]
path_prefix = "/a"
output = ".env.a"
""")
    profiles = load_profiles(config_file)
    assert list_profile_names(profiles) == ["alpha", "zebra"]
