import pytest

from adapters.fakes.llm import FakeClaimExtractionPort, infer_report_export_stated_value
from adapters.fakes.rts import FakeRtsPort
from adapters.fakes.synthetic_data import (
    ANALYTICS_EXPORT_KEY,
    API_RATE_LIMIT_KEY,
    BILLING_REFUND_KEY,
    PLANNED_ONLY_KEY,
    REPORT_EXPORT_KEY,
)
from truthexpiry.ports.rts import EphemeralRtsHits, RtsSearchRequest


def _extract(query: str):
    llm = FakeClaimExtractionPort()
    claims = llm.extract_claims(query, EphemeralRtsHits(hits=()))
    assert len(claims) == 1
    return claims[0]


@pytest.mark.parametrize(
    ("query", "expected_value"),
    [
        ("Is report export available on the Starter plan?", "enabled"),
        ("Is report export enabled on the Starter plan?", "enabled"),
        ("Is report export disabled on the Starter plan?", "disabled"),
        ("Is report export unavailable on the Starter plan?", "disabled"),
        ("Is report export not available on the Starter plan?", "disabled"),
        ("Is report export not enabled on the Starter plan?", "disabled"),
    ],
)
def test_report_export_availability_wording(query: str, expected_value: str):
    claim = _extract(query)
    assert claim.key == REPORT_EXPORT_KEY
    assert claim.stated_value == expected_value


def test_negative_wording_takes_precedence_over_positive_substrings():
    assert (
        infer_report_export_stated_value(
            "is report export not available on the starter plan?"
        )
        == "disabled"
    )
    assert (
        infer_report_export_stated_value(
            "is report export disabled but available elsewhere?"
        )
        == "disabled"
    )


def test_ambiguous_report_export_defaults_to_enabled():
    claim = _extract("What is the report export policy on starter?")
    assert claim.key == REPORT_EXPORT_KEY
    assert claim.stated_value == "enabled"


def test_on_token_does_not_match_arbitrary_substrings():
    assert infer_report_export_stated_value("is report export on starter?") == "enabled"
    assert (
        infer_report_export_stated_value("is report export information accurate?")
        == "enabled"
    )


@pytest.mark.parametrize(
    ("query", "expected_key", "expected_value"),
    [
        ("What is the API rate limit for starter?", API_RATE_LIMIT_KEY, "100"),
        (
            "What is the enterprise refund policy conflict?",
            BILLING_REFUND_KEY,
            "30_days",
        ),
        ("Is analytics export available?", ANALYTICS_EXPORT_KEY, "enabled"),
        ("Is mobile push planned?", PLANNED_ONLY_KEY, "enabled"),
        ("What is the weather today?", PLANNED_ONLY_KEY, "enabled"),
    ],
)
def test_unrelated_fake_claim_scenarios_unchanged(
    query: str, expected_key, expected_value: str
):
    claim = _extract(query)
    assert claim.key == expected_key
    assert claim.stated_value == expected_value


def test_extractor_uses_sanitized_rts_hits_for_evidence_refs():
    llm = FakeClaimExtractionPort()
    hits = FakeRtsPort().search_context(
        RtsSearchRequest(query="report export", action_token="token", team_id="T000")
    )
    claims = llm.extract_claims("Is report export disabled on the Starter plan?", hits)
    assert llm.extract_calls[0][1] == hits
    assert claims[0].stated_value == "disabled"
    assert claims[0].evidence_refs
