from __future__ import annotations

import pytest

from lifecycle_mcp.server_settings import LifecycleMcpServerSettings
from truthexpiry.config import ConfigError

_AUTH_MARKER = "mcp-MARKER-AUTH-SECRET"


def test_existing_host_port_defaults_remain_correct():
    settings = LifecycleMcpServerSettings.from_env({})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_default_auth_enabled_mode_requires_token():
    settings = LifecycleMcpServerSettings.from_env({})
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required"
    ):
        settings.validate_runtime()


def test_explicit_auth_disabled_local_mode_does_not_require_token():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1"}
    )
    settings.validate_runtime()


def test_blank_token_fails_when_auth_enabled():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": "   "}
    )
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required"
    ):
        settings.validate_runtime()


def test_host_blank_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_HOST is required"
    ):
        LifecycleMcpServerSettings.from_env(
            {
                "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST": "   ",
                "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1",
            }
        )


def test_mcp_port_validation():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_PORT": "9000"}
    )
    assert settings.port == 9000


def test_health_port_validation():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT": "9001"}
    )
    assert settings.health_port == 9001


def test_mcp_and_health_ports_cannot_be_equal():
    settings = LifecycleMcpServerSettings.from_env(
        {
            "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT": "8000",
            "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT": "8000",
            "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1",
        }
    )
    with pytest.raises(ConfigError, match="must differ"):
        settings.validate_runtime()


def test_shutdown_timeout_must_be_positive():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_MCP_SHUTDOWN_SECONDS must be greater than"
    ):
        LifecycleMcpServerSettings.from_env({"TRUTH_EXPIRY_MCP_SHUTDOWN_SECONDS": "0"})


def test_dataset_path_is_optional():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1"}
    )
    assert settings.dataset_path is None
    settings.validate_runtime()


def test_mcp_settings_repr_and_str_exclude_token():
    settings = LifecycleMcpServerSettings.from_env(
        {"TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": _AUTH_MARKER}
    )
    for rendered in (repr(settings), str(settings)):
        assert _AUTH_MARKER not in rendered


def test_mcp_settings_require_no_slack_openai_variables():
    settings = LifecycleMcpServerSettings.from_env(
        {
            "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1",
            "SLACK_BOT_TOKEN": "xoxb-should-not-matter",
            "OPENAI_API_KEY": "sk-should-not-matter",
        }
    )
    settings.validate_runtime()
