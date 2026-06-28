from truthexpiry.models.verdict import ClaimStatus
from truthexpiry.services.pipeline import TruthExpiryPipeline, TruthExpiryRequest

import pytest

from adapters.composition import LiveAdaptersUnavailableError, build_pipeline
from adapters.fakes.rts import FakeRtsPort


def test_pipeline_report_export_is_current(pipeline: TruthExpiryPipeline):
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on the starter plan?",
            action_token="action-token",
        )
    )
    assert response.results
    assert response.results[0].status is ClaimStatus.CURRENT
    assert "CURRENT" in response.markdown_text


def test_pipeline_rate_limit_is_superseded(pipeline: TruthExpiryPipeline):
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="What is the API rate limit for starter?",
        )
    )
    assert response.results[0].status is ClaimStatus.SUPERSEDED


def test_pipeline_billing_conflict(pipeline: TruthExpiryPipeline):
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="What is the enterprise refund policy conflict?",
        )
    )
    assert response.results[0].status is ClaimStatus.CONFLICTING
    assert "- PROD-520-A" in response.markdown_text
    assert "- PROD-520-B" in response.markdown_text


def test_build_pipeline_requires_explicit_fakes_or_mcp_url(no_fake_env: None):
    with pytest.raises(LiveAdaptersUnavailableError):
        build_pipeline(use_fakes=False)


def test_pipeline_uses_keyword_fallback_when_semantic_disabled(fixed_clock):
    rts = FakeRtsPort(is_ai_search_enabled=False)
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
    assert rts.search_calls[0].disable_semantic_search is True
