import inspect
import logging

import pytest

from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
from adapters.llm.contracts import ClaimExtractionOutputDto, ExtractedClaimDto
from adapters.llm.errors import (
    MalformedStructuredOutputError,
    ProviderTimeoutError,
    ProviderTransportError,
)
from adapters.llm.fallback_evidence import (
    MAX_FALLBACK_EVIDENCE_REFS,
    build_fallback_evidence_refs,
    select_fallback_evidence_ids,
)
from adapters.llm.mapper import map_extracted_claim_dto
from truthexpiry.models.verdict import ClaimStatus
from truthexpiry.ports.llm import ClaimExtractionUnavailableError
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits
from truthexpiry.services.claim_schema import lookup_claim_schema
from truthexpiry.services.pipeline import TruthExpiryRequest
from truthexpiry.services.query_claim_fallback import extract_grounded_claim_from_query
from truthexpiry.services.query_grounding import (
    availability_polarities_in_query,
    ground_availability_polarity,
    ground_numeric_values,
)

from adapters.composition import build_pipeline
from adapters.fakes.rts import FakeRtsPort
from tests.conftest import FixedClock
from tests.fakes.extraction_runner import FakeExtractionRunner, make_claim_output


def _schema(entity: str, attribute: str):
    return lookup_claim_schema(entity, attribute)


def _hit(
    content: str = "ignored-body",
    *,
    ts: str = "1.0",
    permalink: str = "https://example.invalid/p/1",
) -> EphemeralRtsHit:
    return EphemeralRtsHit(
        team_id="T000",
        channel_id="C000",
        channel_name="demo",
        message_ts=ts,
        permalink=permalink,
        content=content,
    )


def _evidence_map(*hits: EphemeralRtsHit) -> dict[str, EphemeralRtsHit]:
    return {f"evidence-{index}": hit for index, hit in enumerate(hits, start=1)}


# --- Fallback isolation ---


def test_fallback_helper_accepts_query_text_only():
    signature = inspect.signature(extract_grounded_claim_from_query)
    assert list(signature.parameters) == ["query"]


def test_null_model_output_may_activate_fallback():
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is the API rate limit 100 requests for Starter?",
        EphemeralRtsHits(hits=(_hit(),)),
    )
    assert len(claims) == 1
    assert claims[0].stated_value == "100"


@pytest.mark.parametrize(
    "error",
    [
        ProviderTimeoutError("timeout"),
        ProviderTransportError("transport"),
        MalformedStructuredOutputError("bad"),
    ],
)
def test_provider_failures_do_not_activate_fallback(error: Exception):
    runner = FakeExtractionRunner(error=error)
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims(
            "Is the API rate limit 100 requests for Starter?",
            EphemeralRtsHits(hits=(_hit(),)),
        )


def test_invalid_model_claim_does_not_activate_fallback():
    runner = FakeExtractionRunner(
        output=make_claim_output(stated_value="enabled", scope={})
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "Is report export disabled on the Starter plan?",
        EphemeralRtsHits(hits=(_hit(),)),
    )
    assert claims == []


def test_fabricated_evidence_id_does_not_activate_fallback():
    runner = FakeExtractionRunner(
        output=make_claim_output(evidence_ids=["evidence-99"])
    )
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with pytest.raises(ClaimExtractionUnavailableError):
        adapter.extract_claims(
            "Is report export available on the Starter plan?",
            EphemeralRtsHits(hits=(_hit(),)),
        )


def test_internal_programming_error_propagates():
    class BrokenRunner:
        def run(self, *, system_prompt: str, user_prompt: str):
            raise RuntimeError("internal bug")

    adapter = PydanticAiClaimExtractionAdapter(runner=BrokenRunner())
    with pytest.raises(RuntimeError, match="internal bug"):
        adapter.extract_claims(
            "Is report export available on the Starter plan?",
            EphemeralRtsHits(hits=(_hit(),)),
        )


# --- Availability grounding ---


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Is report export available on Starter?", "enabled"),
        ("Is report export enabled on Starter?", "enabled"),
        ("Is report export turned on on Starter?", "enabled"),
        ("Is report export switched on on Starter?", "enabled"),
        ("Is report export on Starter?", "enabled"),
        ("Is report export disabled on Starter?", "disabled"),
        ("Is report export unavailable on Starter?", "disabled"),
        ("Is report export not available on Starter?", "disabled"),
        ("Is report export not enabled on Starter?", "disabled"),
        ("Is report export turned off on Starter?", "disabled"),
        ("Is report export switched off on Starter?", "disabled"),
        ("Is report export off on Starter?", "disabled"),
    ],
)
def test_availability_queries_ground_expected_polarity(query: str, expected: str):
    claim = extract_grounded_claim_from_query(query)
    assert claim is not None
    assert claim.stated_value == expected


def test_negative_phrase_precedence():
    assert (
        ground_availability_polarity("is report export not available on starter?")
        == "disabled"
    )


@pytest.mark.parametrize(
    "query",
    [
        "Is report export available or disabled on Starter?",
        "Report export is disabled but available elsewhere.",
        "Report export is enabled and disabled.",
        "Report export is disabled; previously it was available.",
        "is report export disabled but available elsewhere?",
    ],
)
def test_conflicting_polarity_queries_return_no_claim(query: str):
    assert ground_availability_polarity(query) is None
    assert extract_grounded_claim_from_query(query) is None


def test_on_and_off_word_boundaries():
    assert ground_availability_polarity("is report export on starter?") == "enabled"
    assert (
        ground_availability_polarity("is report export information accurate?") is None
    )
    assert (
        ground_availability_polarity("is report export off on starter?") == "disabled"
    )


def test_conflicting_availability_returns_no_claim():
    assert (
        extract_grounded_claim_from_query(
            "Is report export available or disabled on Starter?"
        )
        is None
    )
    assert (
        availability_polarities_in_query(
            "Is report export available or disabled on Starter?"
        )
        == frozenset()
    )


def test_informational_report_export_returns_no_claim():
    assert (
        extract_grounded_claim_from_query("Tell me about report export on Starter.")
        is None
    )


# --- Numeric grounding ---


def test_explicit_numeric_values():
    assert (
        extract_grounded_claim_from_query(
            "Is the API rate limit 100 requests for Starter?"
        ).stated_value
        == "100"
    )
    assert (
        extract_grounded_claim_from_query(
            "Is the API rate limit 50 requests for Starter?"
        ).stated_value
        == "50"
    )


def test_rate_limit_without_number_returns_no_claim():
    assert (
        extract_grounded_claim_from_query("What is the API rate limit for Starter?")
        is None
    )


def test_unsupported_numeric_returns_no_claim():
    assert (
        extract_grounded_claim_from_query(
            "Is the API rate limit 75 requests for Starter?"
        )
        is None
    )


def test_conflicting_supported_numbers_return_no_claim():
    schema = _schema("api_rate_limit", "max_requests")
    assert schema is not None
    assert (
        len(
            ground_numeric_values(
                "Is the API rate limit 50 or 100 requests for Starter?",
                schema.allowed_stated_values,
            )
        )
        > 1
    )
    assert (
        extract_grounded_claim_from_query(
            "Is the API rate limit 50 or 100 requests for Starter?"
        )
        is None
    )


def test_slack_evidence_cannot_supply_number_when_query_omits_it():
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        "What is the API rate limit for Starter?",
        EphemeralRtsHits(hits=(_hit("Starter API rate limit is 100 requests."),)),
    )
    assert claims == []


# --- Scope and entity grounding ---


def test_starter_plan_from_query_text():
    claim = extract_grounded_claim_from_query("Is report export available on Starter?")
    assert claim is not None
    assert claim.scope["plan"] == "starter"
    assert claim.scope["region"] == "global"


def test_ambiguous_entity_returns_no_claim():
    assert (
        extract_grounded_claim_from_query(
            "Is report export and API rate limit 100 on Starter?"
        )
        is None
    )


def test_unsupported_entity_returns_no_claim():
    assert extract_grounded_claim_from_query("What is the weather today?") is None


@pytest.mark.parametrize(
    "evidence_content",
    [
        "Report export is disabled on the Starter plan.",
        "Report export is disabled on the Enterprise plan.",
    ],
)
def test_evidence_cannot_supply_missing_plan(evidence_content: str):
    query = "Is report export disabled?"
    assert extract_grounded_claim_from_query(query) is None
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    claims = adapter.extract_claims(
        query,
        EphemeralRtsHits(hits=(_hit(evidence_content),)),
    )
    assert claims == []


# --- Evidence separation ---


def test_fallback_evidence_selection_ignores_content():
    evidence_map = _evidence_map(
        _hit("body-1", ts="2.0", permalink="https://example.invalid/p/2"),
        _hit("body-2", ts="1.0", permalink="https://example.invalid/p/1"),
    )
    selected = select_fallback_evidence_ids(evidence_map)
    assert selected == ["evidence-1", "evidence-2"]


def test_fallback_evidence_content_does_not_change_claim():
    grounded = extract_grounded_claim_from_query(
        "Is report export available on Starter?"
    )
    assert grounded is not None
    dto = ExtractedClaimDto(
        entity=grounded.entity,
        attribute=grounded.attribute,
        scope=dict(grounded.scope),
        stated_value=grounded.stated_value,
        evidence_ids=["evidence-1"],
    )
    claim_a = map_extracted_claim_dto(
        dto,
        evidence_map=_evidence_map(_hit("enabled PROD-481")),
    )
    claim_b = map_extracted_claim_dto(
        dto,
        evidence_map=_evidence_map(_hit("disabled PROD-482")),
    )
    assert claim_a.stated_value == claim_b.stated_value == "enabled"
    assert claim_a.key == claim_b.key


def test_fallback_refs_are_capped():
    hits = tuple(
        _hit(
            f"body-{index}",
            ts=f"{index}.0",
            permalink=f"https://example.invalid/p/{index}",
        )
        for index in range(1, 6)
    )
    refs = build_fallback_evidence_refs(_evidence_map(*hits))
    assert len(refs) == MAX_FALLBACK_EVIDENCE_REFS


def test_duplicate_evidence_refs_are_deduplicated():
    shared = "https://example.invalid/p/shared"
    refs = build_fallback_evidence_refs(
        _evidence_map(
            _hit("body-1", ts="1.0", permalink=shared),
            _hit("body-2", ts="1.0", permalink=shared),
        )
    )
    assert len(refs) == 1
    assert refs[0].value == shared


def test_unique_evidence_refs_preserve_rts_order():
    refs = build_fallback_evidence_refs(
        _evidence_map(
            _hit("body-1", ts="1.0", permalink="https://example.invalid/p/1"),
            _hit("body-2", ts="2.0", permalink="https://example.invalid/p/2"),
        )
    )
    assert [ref.value for ref in refs] == [
        "https://example.invalid/p/1",
        "https://example.invalid/p/2",
    ]


def test_duplicate_refs_before_cap_do_not_reduce_later_unique_refs():
    shared = "https://example.invalid/p/shared"
    refs = build_fallback_evidence_refs(
        _evidence_map(
            _hit("body-1", ts="1.0", permalink=shared),
            _hit("body-2", ts="1.0", permalink=shared),
            _hit("body-3", ts="3.0", permalink="https://example.invalid/p/3"),
            _hit("body-4", ts="4.0", permalink="https://example.invalid/p/4"),
            _hit("body-5", ts="5.0", permalink="https://example.invalid/p/5"),
        )
    )
    assert [ref.value for ref in refs] == [
        shared,
        "https://example.invalid/p/3",
        "https://example.invalid/p/4",
    ]


def test_no_sanitizable_refs_produces_no_claim():
    adapter = PydanticAiClaimExtractionAdapter(
        runner=FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    )
    claims = adapter.extract_claims(
        "Is the API rate limit 100 requests for Starter?",
        EphemeralRtsHits(hits=()),
    )
    assert claims == []


# --- Pipeline acceptance ---


def _pipeline_with_runner(runner: FakeExtractionRunner, query: str):
    llm = PydanticAiClaimExtractionAdapter(runner=runner)
    pipeline = build_pipeline(
        clock=FixedClock(__import__("datetime").date(2026, 6, 15)),
        use_fakes=True,
        rts=FakeRtsPort(),
        llm=llm,  # type: ignore[arg-type]
    )
    return pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query=query,
        )
    )


def test_null_available_pipeline_superseded():
    response = _pipeline_with_runner(
        FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None)),
        "Is report export available on the Starter plan?",
    )
    assert "SUPERSEDED" in response.markdown_text
    assert "- PROD-482" in response.markdown_text


def test_null_disabled_pipeline_current():
    response = _pipeline_with_runner(
        FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None)),
        "Is report export disabled on the Starter plan?",
    )
    assert response.results[0].status is ClaimStatus.CURRENT
    assert "- PROD-482" in response.markdown_text


def test_null_informational_pipeline_no_claim():
    response = _pipeline_with_runner(
        FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None)),
        "Tell me about report export on the Starter plan.",
    )
    assert "No structured claims were extracted" in response.markdown_text


def test_null_rate_limit_question_no_claim():
    response = _pipeline_with_runner(
        FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None)),
        "What is the API rate limit for Starter?",
    )
    assert "No structured claims were extracted" in response.markdown_text


def test_null_explicit_rate_limit_superseded():
    response = _pipeline_with_runner(
        FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None)),
        "Is the API rate limit 100 requests for Starter?",
    )
    assert response.results[0].status is ClaimStatus.SUPERSEDED
    assert "- PROD-511" in response.markdown_text


def test_fallback_never_assigns_validity_labels_in_adapter():
    source = inspect.getsource(
        PydanticAiClaimExtractionAdapter._interpret_null_model_output
    )
    for label in ("CURRENT", "SUPERSEDED", "CONFLICTING", "UNVERIFIED"):
        assert label not in source


# --- Privacy ---

_FALLBACK_PRIVACY_MARKERS = {
    "query": "marker-query-fallback-privacy-7f3a",
    "evidence": "marker-evidence-fallback-privacy-7f3a",
    "prompt": "marker-prompt-fallback-privacy-7f3a",
    "provider": "marker-provider-fallback-privacy-7f3a",
    "permalink": "https://example.invalid/p/marker-fallback-privacy-7f3a",
}


def _assert_fallback_logs_are_safe(caplog: pytest.LogCaptureFixture) -> None:
    for marker in _FALLBACK_PRIVACY_MARKERS.values():
        assert marker not in caplog.text
    assert "method=extract_claims" in caplog.text
    assert "outcome=query_fallback_" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "evidence_count=" in caplog.text
    assert "query_length=" in caplog.text
    assert "claim_count=" in caplog.text


def test_fallback_success_logs_exclude_sensitive_markers(
    caplog: pytest.LogCaptureFixture,
):
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.INFO):
        adapter.extract_claims(
            (
                "Is the API rate limit 100 requests for Starter? "
                f"{_FALLBACK_PRIVACY_MARKERS['query']} "
                f"{_FALLBACK_PRIVACY_MARKERS['prompt']}"
            ),
            EphemeralRtsHits(
                hits=(
                    _hit(
                        f"{_FALLBACK_PRIVACY_MARKERS['evidence']} "
                        f"{_FALLBACK_PRIVACY_MARKERS['provider']}",
                        permalink=_FALLBACK_PRIVACY_MARKERS["permalink"],
                    ),
                )
            ),
        )
    _assert_fallback_logs_are_safe(caplog)
    assert "outcome=query_fallback_success" in caplog.text


def test_fallback_no_claim_logs_exclude_sensitive_markers(
    caplog: pytest.LogCaptureFixture,
):
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.INFO):
        adapter.extract_claims(
            f"Tell me about report export {_FALLBACK_PRIVACY_MARKERS['query']}",
            EphemeralRtsHits(
                hits=(
                    _hit(
                        _FALLBACK_PRIVACY_MARKERS["evidence"],
                        permalink=_FALLBACK_PRIVACY_MARKERS["permalink"],
                    ),
                )
            ),
        )
    _assert_fallback_logs_are_safe(caplog)
    assert "outcome=query_fallback_no_claim" in caplog.text


def test_fallback_logs_exclude_sensitive_data(caplog: pytest.LogCaptureFixture):
    secret_query = "secret-query-text"
    secret_body = "secret-evidence-body"
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.INFO):
        adapter.extract_claims(
            secret_query,
            EphemeralRtsHits(
                hits=(
                    _hit(
                        secret_body,
                        permalink="https://example.invalid/p/secret",
                    ),
                )
            ),
        )
    for sensitive in (secret_query, secret_body, "https://example.invalid/p/secret"):
        assert sensitive not in caplog.text


def test_adapter_does_not_retain_request_state():
    runner = FakeExtractionRunner(output=ClaimExtractionOutputDto(claim=None))
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    adapter.extract_claims(
        "Is the API rate limit 100 requests for Starter?",
        EphemeralRtsHits(hits=(_hit(),)),
    )
    assert not hasattr(adapter, "_last_prompt")
    assert not hasattr(adapter, "_last_output")
