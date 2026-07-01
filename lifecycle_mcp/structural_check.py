from __future__ import annotations

import sys
from pathlib import Path

from lifecycle_mcp.server_settings import LifecycleMcpServerSettings
from truthexpiry.config import ConfigError


def run_structural_check() -> int:
    """Parse MCP server configuration without requiring runtime credentials."""
    try:
        LifecycleMcpServerSettings.from_env()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    settings = LifecycleMcpServerSettings.from_env()
    if settings.dataset_path is not None:
        path = Path(settings.dataset_path)
        if not path.is_file():
            print(
                "TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_PATH must reference an existing file",
                file=sys.stderr,
            )
            return 1

    print("Configuration structure: OK")
    return 0


def parse_cli_args(argv: list[str] | None = None) -> bool:
    args = sys.argv if argv is None else argv
    return len(args) > 1 and args[1] == "--check"
