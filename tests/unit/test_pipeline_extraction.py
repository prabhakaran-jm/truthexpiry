from adapters.composition import build_pipeline
from adapters.fakes.rts import FakeRtsPort
from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.llm.contracts import ClaimExtractionOutputDto
from truthexpiry.ports.llm import ClaimExtractionUnavailableError
from truthexpiry.services.pipeline import TruthExpiryRequest

from tests.fakes.extraction_runner import FakeExtractionRunner, make_claim_output


class _UnavailableExtractor:
    def extract_claims(self, query, hits):
        raise ClaimExtractionUnavailableError(
            "Claim extraction is temporarily unavailable for this request."
        )


def test_extraction_unavailable_returns_generic_message(fixed_clock):
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=True,
        rts=FakeRtsPort(),
        llm=_UnavailableExtractor(),  # type: ignore[arg-type]
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on starter?",
        )
    )
    assert "Claim extraction is temporarily unavailable" in response.markdown_text
    assert response.results == ()


def test_unavailable_message_contains_no_provider_or_configuration_details(fixed_clock):
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=True,
        rts=FakeRtsPort(),
        llm=_UnavailableExtractor(),  # type: ignore[arg-type]
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="query",
        )
    )
    lowered = response.markdown_text.lower()
    for forbidden in ("openai", "api key", "mcp", "anthropic", "model"):
        assert forbidden not in lowered


def test_successful_null_claim_uses_existing_no_claim_message(fixed_clock):
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=True,
        rts=FakeRtsPort(),
        llm=llm,  # type: ignore[arg-type]
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Tell me about report export on starter",
        )
    )
    assert "Try one of these example questions" in response.markdown_text
    assert response.results == ()


def test_deterministic_labeler_remains_responsible_for_status(fixed_clock):
    from datetime import date

    from tests.conftest import FixedClock

    runner = FakeExtractionRunner(output=make_claim_output(stated_value="enabled"))
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(date(2026, 6, 15)),
        use_fakes=True,
        rts=FakeRtsPort(),
        llm=llm,  # type: ignore[arg-type]
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on starter?",
        )
    )
    assert response.results
    assert "SUPERSEDED" in response.markdown_text
