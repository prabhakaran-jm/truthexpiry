import pytest
from slack_sdk import WebClient

from adapters.composition import LiveAdaptersUnavailableError, build_pipeline
from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.fakes.rts import FakeRtsPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.slack_rts.adapter import SlackRtsAdapter


def test_build_pipeline_uses_all_fakes_when_flag_set(fixed_clock):
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True)
    assert isinstance(pipeline._lifecycle, FakeLifecycleEvidenceAdapter)
    assert isinstance(pipeline._rts, FakeRtsPort)


def test_build_pipeline_uses_real_lifecycle_when_url_present(
    fixed_clock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("TRUTH_EXPIRY_USE_FAKES", raising=False)
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
    )
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)
    assert isinstance(pipeline._rts, SlackRtsAdapter)


def test_build_pipeline_requires_mcp_url_when_fakes_disabled(no_fake_env: None):
    with pytest.raises(
        LiveAdaptersUnavailableError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_URL"
    ):
        build_pipeline(use_fakes=False, slack_client=WebClient(token="xoxb-test"))


def test_build_pipeline_requires_slack_client_when_fakes_disabled(no_fake_env: None):
    with pytest.raises(LiveAdaptersUnavailableError, match="injected Slack WebClient"):
        build_pipeline(use_fakes=False, lifecycle_mcp_url="http://127.0.0.1:8000/mcp")
