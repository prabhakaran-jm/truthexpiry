#!/usr/bin/env python3
"""TruthExpiry demo preflight command-line entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from truthexpiry.demo.preflight import (  # noqa: E402
    EXIT_REPOSITORY,
    PROFILE_BACKUP_A,
    PROFILE_BACKUP_B,
    PROFILE_LIVE,
    PreflightOptions,
    render_report,
    run_preflight,
    validate_health_base,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether this machine is prepared to begin a TruthExpiry demo.",
    )
    parser.add_argument(
        "--profile",
        choices=[PROFILE_LIVE, PROFILE_BACKUP_A, PROFILE_BACKUP_B],
        default=PROFILE_LIVE,
        help="Demo profile to validate (default: live).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output.",
    )
    parser.add_argument(
        "--expected-ref",
        help="Optional git tag or commit that HEAD must match.",
    )
    parser.add_argument(
        "--worker-health-base",
        default="http://127.0.0.1:8080",
        help="Worker health probe base URL (default: http://127.0.0.1:8080).",
    )
    parser.add_argument(
        "--mcp-health-base",
        default="http://127.0.0.1:8001",
        help="Lifecycle MCP health probe base URL (default: http://127.0.0.1:8001).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=2.0,
        help="Per-request health probe timeout in seconds (default: 2.0).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root for dataset and git checks.",
    )
    parser.add_argument(
        "--skip-structural",
        action="store_true",
        help="Skip backup-b structural subprocess checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be greater than zero")

    try:
        worker_base = validate_health_base(args.worker_health_base)
        mcp_base = validate_health_base(args.mcp_health_base)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_REPOSITORY

    options = PreflightOptions(
        profile=args.profile,
        json_output=args.json,
        expected_ref=args.expected_ref,
        worker_health_base=worker_base,
        mcp_health_base=mcp_base,
        timeout_seconds=args.timeout_seconds,
        repo_root=args.repo_root.resolve(),
        run_structural_checks=not args.skip_structural,
    )
    report = run_preflight(options)
    print(render_report(report, json_output=args.json))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
