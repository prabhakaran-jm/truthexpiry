from slack_sdk import WebClient

from adapters.composition import build_pipeline
from adapters.fakes.rts import FakeRtsPort
from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.ports.rts import RtsSearchRequest, RtsSearchUnavailableError
from truthexpiry.services.pipeline import TruthExpiryPipeline, TruthExpiryRequest

from adapters.fakes.synthetic_data import SYNTHETIC_PERMALINK


class _UnavailableRts:
    def search_context(self, request: RtsSearchRequest):
        raise RtsSearchUnavailableError("unavailable")


def test_pipeline_makes_single_search_context_call(fixed_clock):
    rts = FakeRtsPort()
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True, rts=rts)
    pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on the starter plan?",
            action_token="action-token",
        )
    )
    assert len(rts.search_calls) == 1


def test_pipeline_does_not_invoke_legacy_capabilities_lookup(fixed_clock):
    rts = FakeRtsPort()
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True, rts=rts)
    pipeline.handle(
        TruthExpiryRequest(
            team_id="T000",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="report export starter plan",
        )
    )
    assert len(rts.search_calls) == 1
    assert not hasattr(rts, "capability_calls")


def test_pipeline_unavailable_search_message(fixed_clock):
    pipeline = TruthExpiryPipeline(
        rts=_UnavailableRts(),
        lifecycle=build_pipeline(use_fakes=True)._lifecycle,
        llm=build_pipeline(use_fakes=True)._llm,
        clock=fixed_clock,
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="report export",
            action_token="token",
        )
    )
    assert "Live Slack search is currently unavailable" in response.markdown_text
    assert response.results == ()


def test_pipeline_renders_source_permalink(fixed_clock):
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True)
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on the starter plan?",
        )
    )
    assert SYNTHETIC_PERMALINK in response.markdown_text


def test_live_pipeline_uses_slack_adapter_when_configured(
    fixed_clock, no_fake_env: None
):
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        slack_client=WebClient(token="xoxb-test"),
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
    )
    assert isinstance(pipeline._rts, SlackRtsAdapter)
