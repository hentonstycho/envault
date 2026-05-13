"""Configuration loading for envault."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tomllib

DEFAULT_CONFIG_FILE = "envault.toml"
DEFAULT_ENV_FILE = ".env"
DEFAULT_AWS_REGION = "us-east-1"


@dataclass
class EnvaultConfig:
    """Holds envault configuration parsed from envault.toml."""

    ssm_path: str
    env_file: str = DEFAULT_ENV_FILE
    aws_region: str = DEFAULT_AWS_REGION
    aws_profile: Optional[str] = None
    strip_path_prefix: bool = True
    extra_vars: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ssm_path.startswith("/"):
            raise ValueError(f"ssm_path must start with '/': {self.ssm_path!r}")


def load_config(config_path: Optional[str] = None) -> EnvaultConfig:
    """Load configuration from a TOML file.

    Args:
        config_path: Path to the config file. Defaults to envault.toml in cwd.

    Returns:
        An EnvaultConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        KeyError: If required fields are missing.
    """
    path = Path(config_path or DEFAULT_CONFIG_FILE)

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. "
            "Run 'envault init' to create one."
        )

    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    envault_section = raw.get("envault", {})

    return EnvaultConfig(
        ssm_path=envault_section["ssm_path"],
        env_file=envault_section.get("env_file", DEFAULT_ENV_FILE),
        aws_region=envault_section.get(
            "aws_region",
            os.environ.get("AWS_DEFAULT_REGION", DEFAULT_AWS_REGION),
        ),
        aws_profile=envault_section.get("aws_profile"),
        strip_path_prefix=envault_section.get("strip_path_prefix", True),
        extra_vars=envault_section.get("extra_vars", {}),
    )
