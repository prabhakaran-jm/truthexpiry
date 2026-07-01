"""Tests for exclusive OR query decomposition."""

from truthexpiry.services.query_claim_fallback import extract_grounded_claims_from_query
from truthexpiry.services.query_or_decomposition import iter_query_candidates


def test_iter_query_candidates_splits_availability_or():
    candidates = iter_query_candidates(
        "Is report export available or disabled on the Starter plan?"
    )
    assert candidates == (
        "Is report export available on the Starter plan?",
        "Is report export disabled on the Starter plan?",
    )


def test_extract_grounded_claims_from_or_question_returns_both_polarities():
    claims = extract_grounded_claims_from_query(
        "Is report export available or disabled on the Starter plan?"
    )
    assert len(claims) == 2
    values = {claim.stated_value for claim in claims}
    assert values == {"enabled", "disabled"}


def test_iter_query_candidates_splits_numeric_or():
    candidates = iter_query_candidates(
        "Is the API rate limit 100 or 50 requests for Starter?"
    )
    assert candidates == (
        "Is the API rate limit 100 requests for Starter?",
        "Is the API rate limit 50 requests for Starter?",
    )
