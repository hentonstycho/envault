"""Tests for envault.config module."""

import textwrap
from pathlib import Path

import pytest

from envault.config import EnvaultConfig, load_config


@pytest.fixture()
def config_file(tmp_path: Path):
    """Return a helper that writes a TOML config and returns its path."""

    def _write(content: str) -> Path:
        p = tmp_path / "envault.toml"
        p.write_text(textwrap.dedent(content))
        return p

    return _write


def test_load_minimal_config(config_file):
    path = config_file(
        """
        [envault]
        ssm_path = "/myapp/prod"
        """
    )
    cfg = load_config(str(path))
    assert cfg.ssm_path == "/myapp/prod"
    assert cfg.env_file == ".env"
    assert cfg.aws_region == "us-east-1"
    assert cfg.aws_profile is None
    assert cfg.strip_path_prefix is True
    assert cfg.extra_vars == {}


def test_load_full_config(config_file):
    path = config_file(
        """
        [envault]
        ssm_path = "/myapp/staging"
        env_file = ".env.staging"
        aws_region = "eu-west-1"
        aws_profile = "staging-profile"
        strip_path_prefix = false

        [envault.extra_vars]
        APP_ENV = "staging"
        """
    )
    cfg = load_config(str(path))
    assert cfg.ssm_path == "/myapp/staging"
    assert cfg.env_file == ".env.staging"
    assert cfg.aws_region == "eu-west-1"
    assert cfg.aws_profile == "staging-profile"
    assert cfg.strip_path_prefix is False
    assert cfg.extra_vars == {"APP_ENV": "staging"}


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="envault init"):
        load_config(str(tmp_path / "nonexistent.toml"))


def test_missing_ssm_path_raises(config_file):
    path = config_file(
        """
        [envault]
        env_file = ".env"
        """
    )
    with pytest.raises(KeyError):
        load_config(str(path))


def test_ssm_path_must_start_with_slash():
    with pytest.raises(ValueError, match="must start with"):
        EnvaultConfig(ssm_path="myapp/prod")
