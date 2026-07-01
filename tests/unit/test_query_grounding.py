import logging

import pytest

from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.llm.contracts import ExtractedClaimDto
from adapters.llm.failure_categories import extraction_failure_category
from adapters.llm.mapper import map_extracted_claim_dto
from adapters.llm.errors import InvalidStatedValueError, UnknownEvidenceIdError
from adapters.llm.query_hints import (
    apply_query_hints,
    is_claim_stated_value_grounded_in_query,
)
from adapters.fakes.synthetic_data import API_RATE_LIMIT_KEY
from truthexpiry.models.verdict import ClaimStatus
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits
from truthexpiry.services.claim_schema import (
    lookup_claim_schema,
    normalize_stated_value_for_schema,
)
from truthexpiry.services.query_grounding import (
    ground_availability_polarity,
    ground_numeric_values,
)
from truthexpiry.services.pipeline import TruthExpiryRequest

from adapters.composition import build_pipeline
from adapters.fakes.rts import FakeRtsPort
from tests.conftest import FixedClock
from tests.fakes.extraction_runner import FakeExtractionRunner, make_claim_output


def _schema(entity: str, attribute: str):
    return lookup_claim_schema(entity, attribute)


def _hit(content: str = "Report export enabled PROD-481") -> EphemeralRtsHit:
    return EphemeralRtsHit(
        team_id="T000",
        channel_id="C000",
        channel_name="demo",
        message_ts="1.0",
        permalink="https://example.invalid/p/1",
        content=content,
    )


def _evidence_map():
    return {"evidence-1": _hit()}


def _claim(**overrides) -> ExtractedClaimDto:
    base = {
        "entity": "report_export",
        "attribute": "availability",
        "scope": {"plan": "starter", "region": "global"},
        "stated_value": "enabled",
        "evidence_ids": ["evidence-1"],
    }
    base.update(overrides)
    return ExtractedClaimDto.model_validate(base)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Is report export available on the Starter plan?", "enabled"),
        ("Is report export enabled on the Starter plan?", "enabled"),
        ("Is report export disabled on the Starter plan?", "disabled"),
        ("Is report export unavailable on the Starter plan?", "disabled"),
        ("Is report export not available on the Starter plan?", "disabled"),
        ("Is report export not enabled on the Starter plan?", "disabled"),
        ("Is report export turned off on the Starter plan?", "disabled"),
        ("Is report export switched off on the Starter plan?", "disabled"),
    ],
)
def test_availability_queries_ground_expected_polarity(query: str, expected: str):
    assert ground_availability_polarity(query) == expected


def test_negative_phrases_precede_positive_substrings():
    assert (
        ground_availability_polarity(
            "is report export not available on the starter plan?"
        )
        == "disabled"
    )
    assert (
        ground_availability_polarity(
            "is report export disabled but available elsewhere?"
        )
        is None
    )


def test_on_and_off_use_word_boundaries():
    assert ground_availability_polarity("is report export on starter?") == "enabled"
    assert (
        ground_availability_polarity("is report export information accurate?") is None
    )
    assert (
        ground_availability_polarity("is report export off on starter?") == "disabled"
    )


def test_tell_me_about_has_no_grounded_polarity():
    assert (
        ground_availability_polarity("Tell me about report export on the Starter plan.")
        is None
    )


@pytest.mark.parametrize(
    ("model_value", "query", "grounded"),
    [
        ("enabled", "Is report export available on the Starter plan?", True),
        ("disabled", "Is report export disabled on the Starter plan?", True),
        ("enabled", "Tell me about report export on the Starter plan.", False),
        ("enabled", "Is report export disabled on the Starter plan?", False),
    ],
)
def test_availability_claim_grounding(model_value: str, query: str, grounded: bool):
    claim = _claim(stated_value=model_value)
    assert is_claim_stated_value_grounded_in_query(query, claim) is grounded


def test_rate_limit_value_question_has_no_grounded_numeric():
    schema = _schema("api_rate_limit", "max_requests")
    assert schema is not None
    assert (
        ground_numeric_values(
            "What is the API rate limit for Starter?", schema.allowed_stated_values
        )
        == frozenset()
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Is the API rate limit 100 requests for Starter?", frozenset({"100"})),
        ("Is the API rate limit 50 requests for Starter?", frozenset({"50"})),
    ],
)
def test_explicit_rate_limit_queries_ground_numeric(
    query: str, expected: frozenset[str]
):
    schema = _schema("api_rate_limit", "max_requests")
    assert schema is not None
    assert ground_numeric_values(query, schema.allowed_stated_values) == expected


def test_numeric_phrase_canonicalizes_to_catalog_value():
    schema = _schema("api_rate_limit", "max_requests")
    assert schema is not None
    assert normalize_stated_value_for_schema("100 requests", schema) == "100"


def test_unsupported_numeric_value_fails_validation():
    schema = _schema("api_rate_limit", "max_requests")
    assert schema is not None
    normalized = normalize_stated_value_for_schema("75 requests", schema)
    assert normalized not in schema.allowed_stated_values


def test_tell_me_about_returns_no_claim_even_when_model_returns_enabled():
    runner = FakeExtractionRunner(output=make_claim_output(stated_value="enabled"))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Tell me about report export on the Starter plan.",
        EphemeralRtsHits(hits=(_hit("Report export enabled PROD-481"),)),
    )
    assert claims == []
    assert runner.call_count == 1


def test_rate_limit_value_question_returns_no_claim():
    runner = FakeExtractionRunner(
        output=make_claim_output(
            entity="api_rate_limit",
            attribute="max_requests",
            stated_value="100",
            scope={"plan": "starter", "region": "global"},
        )
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "What is the API rate limit for Starter?",
        EphemeralRtsHits(hits=(_hit("Starter API rate limit is 100 requests."),)),
    )
    assert claims == []


def test_disabled_model_claim_is_not_unavailable():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="disabled", scope={})
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export disabled on the Starter plan?",
        EphemeralRtsHits(hits=(_hit(),)),
    )
    assert len(claims) == 1
    assert claims[0].stated_value == "disabled"


def test_disabled_model_alias_off_is_not_unavailable():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="off", scope={})
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export disabled on the Starter plan?",
        EphemeralRtsHits(hits=(_hit(),)),
    )
    assert len(claims) == 1
    assert claims[0].stated_value == "disabled"


def test_failure_categories_are_safe():
    assert (
        extraction_failure_category(InvalidStatedValueError("bad"))
        == "invalid_stated_value"
    )
    assert (
        extraction_failure_category(UnknownEvidenceIdError("did not resolve"))
        == "evidence_ref_unresolvable"
    )


def test_failure_logs_exclude_sensitive_data(caplog: pytest.LogCaptureFixture):
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
    runner = FakeExtractionRunner(
        output=make_claim_output(entity="unknown", attribute="feature")
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.INFO):
        claims = adapter.extract_claims(secret_query, hits)
    assert claims == []
    for sensitive in (secret_query, secret_body, "https://example.invalid/p/secret"):
        assert sensitive not in caplog.text


def test_available_pipeline_remains_superseded():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="enabled", scope={})
    )
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(__import__("datetime").date(2026, 6, 15)),
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
            query="Is report export available on the Starter plan?",
        )
    )
    assert "SUPERSEDED" in response.markdown_text
    assert "PROD-482" in response.markdown_text


def test_disabled_pipeline_is_current_with_prod_482():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="disabled", scope={})
    )
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(__import__("datetime").date(2026, 6, 15)),
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
            query="Is report export disabled on the Starter plan?",
        )
    )
    assert response.results[0].status is ClaimStatus.CURRENT
    assert "PROD-482" in response.markdown_text


def test_rate_limit_100_pipeline_is_superseded():
    runner = FakeExtractionRunner(
        output=make_claim_output(
            entity="api_rate_limit",
            attribute="max_requests",
            stated_value="100",
            scope={"plan": "starter", "region": "global"},
        )
    )
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(__import__("datetime").date(2026, 6, 15)),
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
            query="Is the API rate limit 100 requests for Starter?",
        )
    )
    assert response.results[0].status is ClaimStatus.SUPERSEDED
    assert "PROD-511" in response.markdown_text


def test_rate_limit_50_pipeline_is_current():
    runner = FakeExtractionRunner(
        output=make_claim_output(
            entity="api_rate_limit",
            attribute="max_requests",
            stated_value="50",
            scope={"plan": "starter", "region": "global"},
        )
    )
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(__import__("datetime").date(2026, 6, 15)),
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
            query="Is the API rate limit 50 requests for Starter?",
        )
    )
    assert response.results[0].status is ClaimStatus.CURRENT
    assert "PROD-511" in response.markdown_text


def test_scope_and_entity_hints_do_not_supply_stated_value():
    claim = apply_query_hints(
        "What is the API rate limit for Starter?",
        _claim(
            entity="api",
            attribute="rate_limit",
            stated_value="100",
        ),
    )
    assert claim.entity == "api_rate_limit"
    assert claim.attribute == "max_requests"
    assert claim.stated_value == "100"
    assert not is_claim_stated_value_grounded_in_query(
        "What is the API rate limit for Starter?", claim
    )


def test_explicit_rate_limit_claim_maps_successfully():
    claim = apply_query_hints(
        "Is the API rate limit 100 requests for Starter?",
        ExtractedClaimDto(
            entity="api",
            attribute="rate_limit",
            scope={},
            stated_value="100 requests",
            evidence_ids=["evidence-1"],
        ),
    )
    mapped = map_extracted_claim_dto(claim, evidence_map=_evidence_map())
    assert mapped.key == API_RATE_LIMIT_KEY
    assert mapped.stated_value == "100"
