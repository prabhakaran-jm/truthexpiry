from __future__ import annotations

import pytest

from truthexpiry.config.common import (
    ConfigError,
    SecretValue,
    parse_bool,
    parse_float,
    parse_int,
    parse_port,
    require_non_blank,
)
from truthexpiry.config.worker import SlackWorkerSettings

_BOT_MARKER = "xoxb-MARKER-BOT-SECRET"
_APP_MARKER = "xapp-MARKER-APP-SECRET"
_OPENAI_MARKER = "sk-MARKER-OPENAI-SECRET"
_MCP_AUTH_MARKER = "mcp-MARKER-AUTH-SECRET"


def _base_worker_env(**overrides: str) -> dict[str, str]:
    env = {
        "SLACK_BOT_TOKEN": _BOT_MARKER,
        "SLACK_APP_TOKEN": _APP_MARKER,
    }
    env.update(overrides)
    return env


def test_required_nonblank_string_accepted():
    assert (
        require_non_blank({"SLACK_BOT_TOKEN": " xoxb-test "}, "SLACK_BOT_TOKEN")
        == "xoxb-test"
    )


def test_blank_required_string_rejected():
    with pytest.raises(ConfigError, match="SLACK_BOT_TOKEN is required"):
        require_non_blank({"SLACK_BOT_TOKEN": "   "}, "SLACK_BOT_TOKEN")


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on", "TRUE", "Yes"])
def test_boolean_true_spellings(raw: str):
    assert parse_bool(
        {"TRUTH_EXPIRY_USE_FAKES": raw}, "TRUTH_EXPIRY_USE_FAKES", default=False
    )


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "FALSE", "Off"])
def test_boolean_false_spellings(raw: str):
    assert not parse_bool(
        {"TRUTH_EXPIRY_USE_FAKES": raw}, "TRUTH_EXPIRY_USE_FAKES", default=True
    )


def test_invalid_boolean_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_USE_FAKES must be a boolean value"
    ):
        parse_bool(
            {"TRUTH_EXPIRY_USE_FAKES": "maybe"}, "TRUTH_EXPIRY_USE_FAKES", default=False
        )


def test_valid_integer_and_float_parsing():
    assert (
        parse_int(
            {"TRUTH_EXPIRY_HEALTH_PORT": "8080"}, "TRUTH_EXPIRY_HEALTH_PORT", default=0
        )
        == 8080
    )
    assert (
        parse_float(
            {"TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS": "30.5"},
            "TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS",
            default=0.0,
            minimum=0.001,
        )
        == 30.5
    )


def test_invalid_integer_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_HEALTH_PORT must be an integer"
    ):
        parse_int(
            {"TRUTH_EXPIRY_HEALTH_PORT": "abc"},
            "TRUTH_EXPIRY_HEALTH_PORT",
            default=8080,
        )


def test_zero_or_negative_timeout_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS must be greater than"
    ):
        parse_float(
            {"TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS": "0"},
            "TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS",
            default=30.0,
            minimum=0.001,
        )


def test_port_lower_boundary():
    assert (
        parse_port(
            {"TRUTH_EXPIRY_HEALTH_PORT": "1"}, "TRUTH_EXPIRY_HEALTH_PORT", default=8080
        )
        == 1
    )


def test_port_upper_boundary():
    assert (
        parse_port(
            {"TRUTH_EXPIRY_HEALTH_PORT": "65535"},
            "TRUTH_EXPIRY_HEALTH_PORT",
            default=8080,
        )
        == 65535
    )


def test_invalid_port_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_HEALTH_PORT must be an integer between"
    ):
        parse_port(
            {"TRUTH_EXPIRY_HEALTH_PORT": "70000"},
            "TRUTH_EXPIRY_HEALTH_PORT",
            default=8080,
        )


def test_config_errors_name_variables_but_not_values():
    marker = "SECRET-MARKER-VALUE-12345"
    with pytest.raises(ConfigError) as exc_info:
        require_non_blank({"SLACK_BOT_TOKEN": "   "}, "SLACK_BOT_TOKEN")
    message = str(exc_info.value)
    assert "SLACK_BOT_TOKEN" in message
    assert marker not in message


def test_secret_value_str_is_redacted():
    secret = SecretValue("super-secret-value")
    assert str(secret) == "SecretValue('********')"


def test_secret_value_repr_is_redacted():
    secret = SecretValue("super-secret-value")
    assert repr(secret) == "SecretValue('********')"


def test_worker_defaults_parse_deterministically():
    settings = SlackWorkerSettings.from_env(_base_worker_env())
    assert settings.use_fakes is False
    assert settings.claim_extractor == "fake"
    assert settings.log_level == "INFO"
    assert settings.log_format == "text"
    assert settings.health_host == "0.0.0.0"
    assert settings.health_port == 8080
    assert settings.metrics_enabled is False
    assert settings.metrics_port == 9090


def test_unset_extractor_defaults_to_fake():
    settings = SlackWorkerSettings.from_env(_base_worker_env())
    assert settings.claim_extractor == "fake"


def test_invalid_extractor_rejected():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_CLAIM_EXTRACTOR must be one of"
    ):
        SlackWorkerSettings.from_env(
            _base_worker_env(TRUTH_EXPIRY_CLAIM_EXTRACTOR="invalid")
        )


def test_runtime_with_fake_adapters_still_requires_slack_bot_token():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_USE_FAKES="1", SLACK_BOT_TOKEN="")
    )
    with pytest.raises(ConfigError, match="SLACK_BOT_TOKEN is required"):
        settings.validate_runtime()


def test_runtime_with_fake_adapters_still_requires_slack_app_token():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_USE_FAKES="1", SLACK_APP_TOKEN="")
    )
    with pytest.raises(ConfigError, match="SLACK_APP_TOKEN is required"):
        settings.validate_runtime()


def test_all_fake_runtime_with_slack_tokens_does_not_require_mcp_url():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_USE_FAKES="1")
    )
    settings.validate_runtime()


def test_all_fake_runtime_with_slack_tokens_does_not_require_mcp_auth_token():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_USE_FAKES="1")
    )
    settings.validate_runtime()


def test_all_fake_runtime_with_slack_tokens_does_not_require_openai_key():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_USE_FAKES="1")
    )
    settings.validate_runtime()


def test_live_pipeline_requires_mcp_url():
    settings = SlackWorkerSettings.from_env(_base_worker_env())
    with pytest.raises(ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_URL is required"):
        settings.validate_runtime()


def test_live_pipeline_requires_mcp_auth_token():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_LIFECYCLE_MCP_URL="http://127.0.0.1:8000/mcp")
    )
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required"
    ):
        settings.validate_runtime()


def test_live_extractor_requires_openai_key():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
            TRUTH_EXPIRY_LIFECYCLE_MCP_URL="http://127.0.0.1:8000/mcp",
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN=_MCP_AUTH_MARKER,
        )
    )
    with pytest.raises(ConfigError, match="OPENAI_API_KEY is required"):
        settings.validate_runtime()


def test_fake_extractor_does_not_require_openai_key():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            TRUTH_EXPIRY_LIFECYCLE_MCP_URL="http://127.0.0.1:8000/mcp",
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN=_MCP_AUTH_MARKER,
        )
    )
    settings.validate_runtime()


def test_blank_openai_key_is_missing():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
            OPENAI_API_KEY="   ",
            TRUTH_EXPIRY_LIFECYCLE_MCP_URL="http://127.0.0.1:8000/mcp",
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN=_MCP_AUTH_MARKER,
        )
    )
    assert settings.openai_api_key is None


def test_blank_mcp_auth_token_is_missing():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            TRUTH_EXPIRY_LIFECYCLE_MCP_URL="http://127.0.0.1:8000/mcp",
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN="   ",
        )
    )
    assert settings.lifecycle_mcp_auth_token is None


def test_settings_repr_excludes_all_four_secret_markers():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            OPENAI_API_KEY=_OPENAI_MARKER,
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN=_MCP_AUTH_MARKER,
        )
    )
    rendered = repr(settings)
    for marker in (_BOT_MARKER, _APP_MARKER, _OPENAI_MARKER, _MCP_AUTH_MARKER):
        assert marker not in rendered


def test_settings_str_excludes_all_four_secret_markers():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            OPENAI_API_KEY=_OPENAI_MARKER,
            TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN=_MCP_AUTH_MARKER,
        )
    )
    rendered = str(settings)
    for marker in (_BOT_MARKER, _APP_MARKER, _OPENAI_MARKER, _MCP_AUTH_MARKER):
        assert marker not in rendered


def test_operational_timeout_defaults_are_correct():
    settings = SlackWorkerSettings.from_env(_base_worker_env())
    assert settings.slack_timeout_seconds == 30.0
    assert settings.mcp_client_timeout_seconds == 10.0
    assert settings.mcp_readiness_timeout_seconds == 60.0
    assert settings.shutdown_drain_seconds == 30.0


def test_invalid_timeout_values_fail():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS must be greater than"
    ):
        SlackWorkerSettings.from_env(
            _base_worker_env(TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS="0")
        )


def test_health_and_metrics_ports_validate():
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(
            TRUTH_EXPIRY_HEALTH_PORT="9091",
            TRUTH_EXPIRY_METRICS_PORT="9092",
        )
    )
    assert settings.health_port == 9091
    assert settings.metrics_port == 9092


def test_explicit_injected_environment_mapping_is_used(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "live")
    settings = SlackWorkerSettings.from_env(
        _base_worker_env(TRUTH_EXPIRY_CLAIM_EXTRACTOR="fake")
    )
    assert settings.claim_extractor == "fake"
