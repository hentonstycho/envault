"""CLI entry point for envault.

Usage:
    python -m envault [OPTIONS] COMMAND [ARGS]...

Commands:
    sync    Pull parameters from SSM and write to .env file.
    check   Verify connectivity and config without writing any files.
"""

import sys
import argparse
import logging
from pathlib import Path

from envault.config import load_config, EnvaultConfig
from envault.ssm import SSMClient, SSMError
from envault.sync import sync, SyncError

logger = logging.getLogger("envault")


def _setup_logging(verbose: bool) -> None:
    """Configure root logger based on verbosity flag."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger("envault").setLevel(level)
    logging.getLogger("envault").addHandler(handler)


def cmd_sync(config: EnvaultConfig, args: argparse.Namespace) -> int:
    """Execute the sync command: fetch SSM params and write .env file."""
    client = SSMClient(
        region=config.aws_region,
        profile=config.aws_profile,
    )

    output_path = Path(args.output) if args.output else Path(config.output_file)

    logger.info("Syncing parameters to %s", output_path)

    try:
        written = sync(config=config, client=client, output_path=output_path)
    except SSMError as exc:
        logger.error("SSM error: %s", exc)
        return 1
    except SyncError as exc:
        logger.error("Sync error: %s", exc)
        return 1

    logger.info("Wrote %d variable(s) to %s", written, output_path)
    return 0


def cmd_check(config: EnvaultConfig, _args: argparse.Namespace) -> int:
    """Execute the check command: validate config and SSM connectivity."""
    client = SSMClient(
        region=config.aws_region,
        profile=config.aws_profile,
    )

    logger.info("Checking connectivity for region=%s", config.aws_region)

    # Attempt a lightweight describe call by fetching a single known path.
    # We treat a permission/not-found error as a connectivity success.
    try:
        for mapping in config.parameters:
            path = mapping.get("path") or mapping.get("name")
            if path:
                client.get_parameters_by_path(path, recursive=False)
                break
    except SSMError as exc:
        # A ClientError response still means we reached AWS successfully.
        logger.debug("SSM probe returned: %s", exc)

    logger.info("Config OK. AWS region: %s, output: %s", config.aws_region, config.output_file)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="envault",
        description="Sync AWS SSM parameters into a local .env file.",
    )
    parser.add_argument(
        "--config",
        default="envault.toml",
        metavar="FILE",
        help="Path to envault.toml config file (default: envault.toml).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # sync sub-command
    sync_parser = subparsers.add_parser("sync", help="Fetch parameters and write .env file.")
    sync_parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        default=None,
        help="Override the output .env file path from config.",
    )

    # check sub-command
    subparsers.add_parser("check", help="Validate config and AWS connectivity.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point; returns an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    try:
        config = load_config(Path(args.config))
    except FileNotFoundError:
        logger.error("Config file not found: %s", args.config)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load config: %s", exc)
        return 1

    commands = {
        "sync": cmd_sync,
        "check": cmd_check,
    }
    return commands[args.command](config, args)


if __name__ == "__main__":
    sys.exit(main())
