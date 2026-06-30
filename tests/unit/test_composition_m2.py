import pytest
from slack_sdk import WebClient

from adapters.composition import LiveAdaptersUnavailableError, build_pipeline
from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.rts import FakeRtsPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.config import SlackWorkerSettings


def _live_settings(**overrides: str) -> SlackWorkerSettings:
    env = {
        "SLACK_BOT_TOKEN": "xoxb-test",
        "SLACK_APP_TOKEN": "xapp-test",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_URL": "http://127.0.0.1:8000/mcp",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": "test-mcp-auth-token",
    }
    env.update(overrides)
    return SlackWorkerSettings.from_env(env)


def test_build_pipeline_uses_all_fakes_when_flag_set(fixed_clock):
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True)
    assert isinstance(pipeline._lifecycle, FakeLifecycleEvidenceAdapter)
    assert isinstance(pipeline._rts, FakeRtsPort)


def test_build_pipeline_uses_real_lifecycle_when_url_present(
    fixed_clock, no_fake_env: None
):
    settings = _live_settings()
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)
    assert isinstance(pipeline._rts, SlackRtsAdapter)
    assert pipeline._lifecycle.auth_token == "test-mcp-auth-token"


def test_build_pipeline_requires_mcp_url_when_fakes_disabled(no_fake_env: None):
    settings = SlackWorkerSettings.from_env(
        {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": "test-mcp-auth-token",
        }
    )
    with pytest.raises(
        LiveAdaptersUnavailableError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_URL"
    ):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            settings=settings,
        )


def test_build_pipeline_requires_mcp_auth_token_when_fakes_disabled(no_fake_env: None):
    settings = _live_settings(TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN="")
    with pytest.raises(
        LiveAdaptersUnavailableError,
        match="TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN is required",
    ):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
            settings=settings,
        )


def test_build_pipeline_requires_slack_client_when_fakes_disabled(no_fake_env: None):
    settings = _live_settings()
    with pytest.raises(LiveAdaptersUnavailableError, match="injected Slack WebClient"):
        build_pipeline(
            use_fakes=False,
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
            settings=settings,
        )
