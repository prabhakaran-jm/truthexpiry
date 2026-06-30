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
)

ClaimExtractor = Literal["fake", "live"]
LogFormat = Literal["text", "json"]

_VALID_CLAIM_EXTRACTORS = frozenset({"fake", "live"})
_VALID_LOG_FORMATS = frozenset({"text", "json"})


@dataclass(frozen=True)
class SlackWorkerSettings:
    """Typed Slack worker configuration.

    ``from_env()`` parses values and validates types only.
    ``validate_runtime()`` enforces credentials for Socket Mode startup.
    A future structural ``--check`` command will parse without calling
    ``validate_runtime()``.
    """

    slack_bot_token: SecretValue | None
    slack_app_token: SecretValue | None
    slack_api_url: str | None
    use_fakes: bool
    claim_extractor: ClaimExtractor
    openai_api_key: SecretValue | None
    lifecycle_mcp_url: str | None
    lifecycle_mcp_health_url: str | None
    lifecycle_mcp_health_port: int
    lifecycle_mcp_auth_token: SecretValue | None
    log_level: str
    log_format: LogFormat
    health_host: str
    health_port: int
    slack_timeout_seconds: float
    mcp_client_timeout_seconds: float
    mcp_readiness_timeout_seconds: float
    shutdown_drain_seconds: float
    metrics_enabled: bool
    metrics_port: int
    dedup_event_ids: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "SlackWorkerSettings":
        mapping = os.environ if env is None else env
        extractor_raw = parse_choice(
            mapping,
            "TRUTH_EXPIRY_CLAIM_EXTRACTOR",
            choices=_VALID_CLAIM_EXTRACTORS,
            default="fake",
        )
        claim_extractor: ClaimExtractor = (
            "fake" if extractor_raw is None else extractor_raw  # type: ignore[assignment]
        )

        log_format_raw = parse_choice(
            mapping,
            "TRUTH_EXPIRY_LOG_FORMAT",
            choices=_VALID_LOG_FORMATS,
            default="text",
        )
        log_format: LogFormat = (
            "text" if log_format_raw is None else log_format_raw  # type: ignore[assignment]
        )

        return cls(
            slack_bot_token=SecretValue.from_optional(
                get_optional_non_blank(mapping, "SLACK_BOT_TOKEN")
            ),
            slack_app_token=SecretValue.from_optional(
                get_optional_non_blank(mapping, "SLACK_APP_TOKEN")
            ),
            slack_api_url=get_optional_non_blank(mapping, "SLACK_API_URL"),
            use_fakes=parse_bool(mapping, "TRUTH_EXPIRY_USE_FAKES", default=False),
            claim_extractor=claim_extractor,
            openai_api_key=SecretValue.from_optional(
                get_optional_non_blank(mapping, "OPENAI_API_KEY")
            ),
            lifecycle_mcp_url=get_optional_non_blank(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_URL"
            ),
            lifecycle_mcp_health_url=get_optional_non_blank(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL"
            ),
            lifecycle_mcp_health_port=parse_port(
                mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT", default=8001
            ),
            lifecycle_mcp_auth_token=SecretValue.from_optional(
                get_optional_non_blank(mapping, "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN")
            ),
            log_level=get_optional_non_blank(mapping, "TRUTH_EXPIRY_LOG_LEVEL")
            or "INFO",
            log_format=log_format,
            health_host=get_optional_non_blank(mapping, "TRUTH_EXPIRY_HEALTH_HOST")
            or "0.0.0.0",
            health_port=parse_port(mapping, "TRUTH_EXPIRY_HEALTH_PORT", default=8080),
            slack_timeout_seconds=parse_float(
                mapping,
                "TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS",
                default=30.0,
                minimum=0.001,
            ),
            mcp_client_timeout_seconds=parse_float(
                mapping,
                "TRUTH_EXPIRY_MCP_CLIENT_TIMEOUT_SECONDS",
                default=10.0,
                minimum=0.001,
            ),
            mcp_readiness_timeout_seconds=parse_float(
                mapping,
                "TRUTH_EXPIRY_MCP_READINESS_TIMEOUT_SECONDS",
                default=60.0,
                minimum=0.001,
            ),
            shutdown_drain_seconds=parse_float(
                mapping,
                "TRUTH_EXPIRY_SHUTDOWN_DRAIN_SECONDS",
                default=30.0,
                minimum=0.001,
            ),
            metrics_enabled=parse_bool(
                mapping, "TRUTH_EXPIRY_METRICS_ENABLED", default=False
            ),
            metrics_port=parse_port(mapping, "TRUTH_EXPIRY_METRICS_PORT", default=9090),
            dedup_event_ids=parse_bool(
                mapping, "TRUTH_EXPIRY_DEDUP_EVENT_IDS", default=False
            ),
        )

    def validate_runtime(self) -> None:
        """Validate credentials required for normal Socket Mode startup."""
        if self.slack_bot_token is None:
            raise ConfigError("SLACK_BOT_TOKEN is required")
        if self.slack_app_token is None:
            raise ConfigError("SLACK_APP_TOKEN is required")
        self._validate_live_pipeline_requirements()

    def validate_for_composition(
        self,
        *,
        use_fakes: bool,
        llm_injected: bool,
        lifecycle_injected: bool,
        lifecycle_mcp_url: str | None,
    ) -> None:
        """Validate only the configuration needed to compose pipeline adapters."""
        if use_fakes:
            return
        if not lifecycle_injected:
            url = lifecycle_mcp_url or self.lifecycle_mcp_url
            if url is None:
                raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_URL is required")
            if self.lifecycle_mcp_auth_token is None:
                raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required")
        if not llm_injected and self.claim_extractor == "live":
            if self.openai_api_key is None:
                raise ConfigError("OPENAI_API_KEY is required")

    def _validate_live_pipeline_requirements(self) -> None:
        if self.use_fakes:
            return
        if self.lifecycle_mcp_url is None:
            raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_URL is required")
        if self.lifecycle_mcp_auth_token is None:
            raise ConfigError("TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required")
        if self.claim_extractor == "live" and self.openai_api_key is None:
            raise ConfigError("OPENAI_API_KEY is required")

    def __str__(self) -> str:
        return (
            "SlackWorkerSettings("
            f"use_fakes={self.use_fakes}, "
            f"claim_extractor={self.claim_extractor!r}, "
            f"log_level={self.log_level!r}, "
            f"log_format={self.log_format!r}, "
            f"health_host={self.health_host!r}, "
            f"health_port={self.health_port}, "
            f"metrics_enabled={self.metrics_enabled}"
            ")"
        )

    def __repr__(self) -> str:
        return self.__str__()
