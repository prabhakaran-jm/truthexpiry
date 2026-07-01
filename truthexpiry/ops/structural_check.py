from __future__ import annotations

import sys

from truthexpiry.config import ConfigError, SlackWorkerSettings


def run_structural_check() -> int:
    """Parse worker configuration without requiring runtime credentials."""
    try:
        SlackWorkerSettings.from_env()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Configuration structure: OK")
    return 0


def parse_cli_args(argv: list[str] | None = None) -> bool:
    """Return True when ``--check`` is requested."""
    args = sys.argv if argv is None else argv
    return "--check" in args
