"""CLI entry-point for envault."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from envault.config import load_config
from envault.rotate import check_rotation
from envault.ssm import SSMClient
from envault.sync import SyncError, sync

logger = logging.getLogger("envault")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s %(message)s", level=level)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_sync(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    client = SSMClient(region=cfg.aws_region, profile=cfg.aws_profile)
    try:
        result = sync(cfg, client)
    except SyncError as exc:
        logger.error("sync failed: %s", exc)
        return 1
    if result.has_changes:
        logger.info(result.summary())
    else:
        logger.info("No changes.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    client = SSMClient(region=cfg.aws_region, profile=cfg.aws_profile)
    try:
        params = client.get_parameters_by_path(cfg.ssm_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("check failed: %s", exc)
        return 1
    logger.info("Found %d parameter(s) under %s", len(params), cfg.ssm_path)
    return 0


def cmd_rotate(args: argparse.Namespace) -> int:
    """Report staleness of synced secrets based on the audit log."""
    cfg = load_config(args.config)
    paths: List[str] = args.paths or [cfg.ssm_path]
    threshold: int = args.threshold
    audit_file: str = args.audit_file or getattr(cfg, "audit_file", "envault-audit.jsonl")

    report = check_rotation(paths, audit_file, threshold_days=threshold)

    for status in report.statuses:
        level = logging.WARNING if status.is_stale else logging.INFO
        logger.log(level, status.summary())

    if report.has_stale:
        logger.warning(
            "%d path(s) are stale (threshold: %d days). Consider re-syncing.",
            len(report.stale_paths),
            threshold,
        )
        return 1
    logger.info("All paths are within the rotation threshold.")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envault",
        description="Sync secrets from AWS SSM Parameter Store into .env files.",
    )
    parser.add_argument("-c", "--config", default="envault.toml", help="Config file path.")
    parser.add_argument("-v", "--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="Sync parameters to .env file.")
    sub.add_parser("check", help="Verify SSM connectivity and list parameters.")

    rot = sub.add_parser("rotate", help="Check whether secrets are due for rotation.")
    rot.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="SSM paths to check (defaults to ssm_path in config).",
    )
    rot.add_argument(
        "--threshold",
        type=int,
        default=30,
        metavar="DAYS",
        help="Number of days before a secret is considered stale (default: 30).",
    )
    rot.add_argument(
        "--audit-file",
        default=None,
        metavar="FILE",
        help="Path to the audit log (overrides config).",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    handlers = {
        "sync": cmd_sync,
        "check": cmd_check,
        "rotate": cmd_rotate,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(0)

    sys.exit(handler(args))


if __name__ == "__main__":  # pragma: no cover
    main()
