import logging

import pytest

from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.llm.contracts import ClaimExtractionOutputDto
from adapters.llm.errors import (
    MalformedStructuredOutputError,
    ProviderTimeoutError,
    ProviderTransportError,
)
from adapters.llm.prompt import MAX_QUERY_CHARACTERS
from truthexpiry.ports.llm import ClaimExtractionUnavailableError
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits

from tests.fakes.extraction_runner import FakeExtractionRunner, make_claim_output


def _hits() -> EphemeralRtsHits:
    return EphemeralRtsHits(
        hits=(
            EphemeralRtsHit(
                team_id="T000",
                channel_id="C000",
                channel_name="demo",
                message_ts="1.0",
                permalink="https://example.invalid/p/1",
                content="Report export enabled on starter",
            ),
        )
    )


def test_successful_one_claim_extraction():
    runner = FakeExtractionRunner(output=make_claim_output())
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims("Is report export available on starter?", _hits())
    assert len(claims) == 1
    assert claims[0].stated_value == "enabled"


def test_live_model_wording_and_missing_scope_are_normalized():
    runner = FakeExtractionRunner(
        output=make_claim_output(
            scope={},
            stated_value="available",
        )
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export available on the Starter plan?",
        _hits(),
    )
    assert len(claims) == 1
    assert claims[0].stated_value == "enabled"
    assert claims[0].key.scope.fields["plan"] == "starter"


def test_informational_query_returns_no_claims_after_grounding_rejection():
    runner = FakeExtractionRunner(output=make_claim_output())
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Tell me about report export on the Starter plan.",
        _hits(),
    )
    assert claims == []
    assert runner.call_count == 1


def test_disabled_query_accepts_matching_model_polarity():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="disabled", scope={})
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export disabled on the Starter plan?",
        _hits(),
    )
    assert len(claims) == 1
    assert claims[0].stated_value == "disabled"


def test_disabled_query_rejects_mismatched_model_polarity():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="enabled", scope={})
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export disabled on the Starter plan?",
        _hits(),
    )
    assert claims == []


def test_explicit_no_claim_output():
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    assert adapter.extract_claims("Tell me about report export", _hits()) == []


def test_runner_invoked_once():
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    adapter.extract_claims("query", _hits())
    assert runner.call_count == 1


def test_provider_timeout_maps_to_unavailable():
    runner = FakeExtractionRunner(error=ProviderTimeoutError("timeout"))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims("query", _hits())
    assert runner.call_count == 1


def test_transport_error_maps_to_unavailable():
    runner = FakeExtractionRunner(error=ProviderTransportError("transport"))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims("query", _hits())


def test_malformed_output_maps_to_unavailable():
    runner = FakeExtractionRunner(error=MalformedStructuredOutputError("bad"))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims("query", _hits())


def test_validation_failures_are_not_retried():
    runner = FakeExtractionRunner(
        output=make_claim_output(entity="unknown", attribute="feature")
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims("What is the weather today?", _hits())
    assert runner.call_count == 1


def test_unsupported_claim_not_retried():
    runner = FakeExtractionRunner(output=make_claim_output(stated_value="not-a-value"))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims(
            "Is report export available on the Starter plan?",
            _hits(),
        )
    assert runner.call_count == 1


def test_internal_programming_error_propagates():
    class BrokenRunner:
        def run(self, *, system_prompt: str, user_prompt: str):
            raise RuntimeError("internal bug")

    adapter = PydanticAiClaimExtractionAdapter(runner=BrokenRunner())
    with pytest.raises(RuntimeError, match="internal bug"):
        adapter.extract_claims("query", _hits())


def test_query_too_long_maps_to_unavailable():
    adapter = PydanticAiClaimExtractionAdapter(
        runner=FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    )
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims("x" * (MAX_QUERY_CHARACTERS + 1), _hits())


def test_no_sensitive_values_logged(caplog: pytest.LogCaptureFixture):
    secret_query = "secret-query-text"
    secret_body = "secret-evidence-body"
    hits = EphemeralRtsHits(
        hits=(
            EphemeralRtsHit(
                team_id="T000",
                channel_id="C000",
                channel_name="demo",
                message_ts="1.0",
                permalink="https://example.invalid/p/secret",
                content=secret_body,
            ),
        )
    )
    runner = FakeExtractionRunner(output=make_claim_output())
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.DEBUG):
        adapter.extract_claims(
            "Is report export available on the Starter plan?",
            hits,
        )
    for sensitive in (
        secret_query,
        secret_body,
        "https://example.invalid/p/secret",
        "OPENAI_API_KEY",
    ):
        assert sensitive not in caplog.text


def test_adapter_does_not_retain_request_state():
    runner = FakeExtractionRunner(output=make_claim_output())
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    adapter.extract_claims("query", _hits())
    assert not hasattr(adapter, "_last_prompt")
    assert not hasattr(adapter, "_last_output")
