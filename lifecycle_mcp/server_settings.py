from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from truthexpiry.config.common import (
    ConfigError,
    SecretValue,
    get_optional_non_blank,
    parse_bool,
    parse_choice,
    parse_float,
    parse_port,
    require_non_blank,
)

LogFormat = Literal["text", "json"]
_VALID_LOG_FORMATS = frozenset({"text", "json"})


@dataclass(frozen=True)
class LifecycleMcpServerSettings:
    host: str
    port: int
    health_port: int
    auth_token: SecretValue | None
    auth_disabled: bool
    log_level: str
    log_format: LogFormat
    shutdown_seconds: float
    dataset_path: str | None
    dataset_hot_reload: bool

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> "LifecycleMcpServerSettings":
        mapping = os.environ if env is None else env

        log_format_raw = parse_choice(
            mapping,
            "TRUTH_EXPIRY_LOG_FORMAT",
            choices=_VALID_LOG_FORMATS,
            default="text",
        )
        log_format: LogFormat = (
            "text" if log_format_raw is None else log_format_raw  # type: ignore[assignment]
        )

        if "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST" in mapping:
            host = require_non_blank(mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST")
        else:
            host = "127.0.0.1"

        return cls(
            host=host,
            port=parse_port(mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT", default=8000),
            health_port=parse_port(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT", default=8001
            ),
            auth_token=SecretValue.from_optional(
                get_optional_non_blank(mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN")
            ),
            auth_disabled=parse_bool(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED", default=False
            ),
            log_level=get_optional_non_blank(mapping, "TRUTH_EXPIRY_LOG_LEVEL")
            or "INFO",
            log_format=log_format,
            shutdown_seconds=parse_float(
                mapping,
                "TRUTH_EXPIRY_MCP_SHUTDOWN_SECONDS",
                default=10.0,
                minimum=0.001,
            ),
            dataset_path=get_optional_non_blank(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_PATH"
            ),
            dataset_hot_reload=parse_bool(
                mapping,
                "TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_HOT_RELOAD",
                default=False,
            ),
        )

    def validate_runtime(self) -> None:
        if not self.host.strip():
            raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_HOST is required")
        if self.port == self.health_port:
            raise ConfigError(
                "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT and "
                "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT must differ"
            )
        if not self.auth_disabled and self.auth_token is None:
            raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required")

    def __str__(self) -> str:
        return (
            "LifecycleMcpServerSettings("
            f"host={self.host!r}, "
            f"port={self.port}, "
            f"health_port={self.health_port}, "
            f"auth_disabled={self.auth_disabled}, "
            f"log_level={self.log_level!r}, "
            f"log_format={self.log_format!r}, "
            f"shutdown_seconds={self.shutdown_seconds}"
            ")"
        )

    def __repr__(self) -> str:
        return self.__str__()
