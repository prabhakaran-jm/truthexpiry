import pytest
from slack_sdk import WebClient

from adapters.composition import LiveAdaptersUnavailableError, build_pipeline
from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter
from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.config import SlackWorkerSettings


class _InjectedExtractor:
    pass


def _live_settings(**overrides: str) -> SlackWorkerSettings:
    env = {
        "SLACK_BOT_TOKEN": "xoxb-test",
        "SLACK_APP_TOKEN": "xapp-test",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_URL": "http://127.0.0.1:8000/mcp",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": "test-mcp-auth-token",
    }
    env.update(overrides)
    return SlackWorkerSettings.from_env(env)


def test_injected_llm_wins_over_every_environment_setting(
    fixed_clock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("TRUTH_EXPIRY_USE_FAKES", "1")
    monkeypatch.setenv("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    injected = _InjectedExtractor()
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True, llm=injected)  # type: ignore[arg-type]
    assert pipeline._llm is injected


def test_all_fakes_override_selects_fake_when_no_injection(fixed_clock, monkeypatch):
    monkeypatch.setenv("TRUTH_EXPIRY_USE_FAKES", "1")
    monkeypatch.setenv("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "live")
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True)
    assert isinstance(pipeline._llm, FakeClaimExtractionPort)


def test_selector_fake_selects_fake(no_fake_env: None, fixed_clock):
    settings = _live_settings(TRUTH_EXPIRY_CLAIM_EXTRACTOR="fake")
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._llm, FakeClaimExtractionPort)
    assert isinstance(pipeline._rts, SlackRtsAdapter)
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)


def test_selector_live_with_openai_key_selects_live(
    no_fake_env: None, fixed_clock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = _live_settings(
        TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
        OPENAI_API_KEY="sk-test",
    )
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._llm, PydanticAiClaimExtractionAdapter)


def test_selector_live_without_key_fails_startup(no_fake_env: None):
    settings = _live_settings(TRUTH_EXPIRY_CLAIM_EXTRACTOR="live")
    with pytest.raises(LiveAdaptersUnavailableError, match="OPENAI_API_KEY"):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
            settings=settings,
        )


def test_blank_openai_key_fails_startup(no_fake_env: None):
    settings = _live_settings(
        TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
        OPENAI_API_KEY="   ",
    )
    with pytest.raises(LiveAdaptersUnavailableError, match="OPENAI_API_KEY"):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
            settings=settings,
        )


def test_invalid_selector_fails_startup(
    no_fake_env: None, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "invalid")
    monkeypatch.setenv("TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN", "test-mcp-auth-token")
    with pytest.raises(
        LiveAdaptersUnavailableError, match="TRUTH_EXPIRY_CLAIM_EXTRACTOR"
    ):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        )


def test_unset_selector_defaults_to_fake(no_fake_env: None, fixed_clock):
    settings = _live_settings()
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._llm, FakeClaimExtractionPort)


def test_anthropic_key_alone_does_not_satisfy_live_mode(no_fake_env: None):
    settings = _live_settings(
        TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="sk-ant-test",
    )
    with pytest.raises(LiveAdaptersUnavailableError, match="OPENAI_API_KEY"):
        build_pipeline(
            use_fakes=False,
            slack_client=WebClient(token="xoxb-test"),
            lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
            settings=settings,
        )


def test_fake_extractor_with_live_rts_and_lifecycle(no_fake_env: None, fixed_clock):
    settings = _live_settings(TRUTH_EXPIRY_CLAIM_EXTRACTOR="fake")
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._llm, FakeClaimExtractionPort)
    assert isinstance(pipeline._rts, SlackRtsAdapter)
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)


def test_only_one_live_extraction_adapter_composed(
    no_fake_env: None, fixed_clock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = _live_settings(
        TRUTH_EXPIRY_CLAIM_EXTRACTOR="live",
        OPENAI_API_KEY="sk-test",
    )
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._llm, PydanticAiClaimExtractionAdapter)
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)


def test_injected_settings_object_controls_adapter_composition(
    no_fake_env: None, fixed_clock
):
    settings = _live_settings(TRUTH_EXPIRY_CLAIM_EXTRACTOR="fake")
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
        settings=settings,
    )
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)
    assert pipeline._lifecycle.auth_token == "test-mcp-auth-token"
    assert pipeline._lifecycle.mcp_url == "http://127.0.0.1:8000/mcp"
