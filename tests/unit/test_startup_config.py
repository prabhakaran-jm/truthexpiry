from __future__ import annotations

from unittest.mock import patch

import pytest
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from lifecycle_mcp.server_settings import LifecycleMcpServerSettings
from truthexpiry.config import ConfigError, SlackWorkerSettings

_BOT_MARKER = "xoxb-MARKER-BOT-SECRET"
_APP_MARKER = "xapp-MARKER-APP-SECRET"
_OPENAI_MARKER = "sk-MARKER-OPENAI-SECRET"
_MCP_AUTH_MARKER = "mcp-MARKER-AUTH-SECRET"


def _valid_worker_env(**overrides: str) -> dict[str, str]:
    env = {
        "SLACK_BOT_TOKEN": _BOT_MARKER,
        "SLACK_APP_TOKEN": _APP_MARKER,
    }
    env.update(overrides)
    return env


def test_worker_invalid_config_fails_before_slack_app_construction():
    settings = SlackWorkerSettings.from_env(_valid_worker_env(SLACK_BOT_TOKEN=""))
    with patch("app.App") as app_cls:
        with pytest.raises(ConfigError, match="SLACK_BOT_TOKEN is required"):
            settings.validate_runtime()
        app_cls.assert_not_called()


def test_worker_invalid_config_fails_before_socket_mode_handler_construction():
    settings = SlackWorkerSettings.from_env(_valid_worker_env(SLACK_APP_TOKEN=""))
    with patch("app.SocketModeHandler") as handler_cls:
        with pytest.raises(ConfigError, match="SLACK_APP_TOKEN is required"):
            settings.validate_runtime()
        handler_cls.assert_not_called()


def test_main_exits_before_app_when_runtime_validation_fails():
    settings = SlackWorkerSettings.from_env(_valid_worker_env(SLACK_BOT_TOKEN=""))
    with patch("app.SlackWorkerSettings.from_env", return_value=settings):
        with patch("app.create_slack_application") as create_app:
            with pytest.raises(SystemExit) as exc_info:
                import app as app_module

                app_module.main()
            assert exc_info.value.code == 1
            create_app.assert_not_called()


def test_mcp_invalid_config_fails_before_fastmcp_run():
    settings = LifecycleMcpServerSettings.from_env({})
    with patch("lifecycle_mcp.server.create_mcp") as create_mcp:
        with pytest.raises(ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN"):
            settings.validate_runtime()
        create_mcp.assert_not_called()


def test_mcp_main_exits_before_run_when_auth_missing():
    settings = LifecycleMcpServerSettings.from_env({})
    with patch(
        "lifecycle_mcp.server.LifecycleMcpServerSettings.from_env",
        return_value=settings,
    ):
        with patch("lifecycle_mcp.server.create_mcp") as create_mcp:
            with pytest.raises(SystemExit) as exc_info:
                from lifecycle_mcp import server as mcp_server

                mcp_server.main()
            assert exc_info.value.code == 1
            create_mcp.assert_not_called()


def test_error_messages_contain_variable_names_but_not_secret_markers(capsys):
    settings = SlackWorkerSettings.from_env(
        _valid_worker_env(
            SLACK_BOT_TOKEN="",
            SLACK_APP_TOKEN=_APP_MARKER,
        )
    )
    with patch("app.SlackWorkerSettings.from_env", return_value=settings):
        with pytest.raises(SystemExit):
            import app as app_module

            app_module.main()
    captured = capsys.readouterr()
    assert "SLACK_BOT_TOKEN" in captured.err
    assert _APP_MARKER not in captured.err


def test_create_slack_application_builds_app_and_handler():
    import importlib
    import sys

    sys.modules.pop("app", None)
    import app as app_module

    importlib.reload(app_module)

    settings = SlackWorkerSettings.from_env(_valid_worker_env())
    with patch.object(WebClient, "auth_test", return_value={"ok": True}):
        app, handler = app_module.create_slack_application(settings)
    assert isinstance(app, App)
    assert isinstance(handler, SocketModeHandler)
