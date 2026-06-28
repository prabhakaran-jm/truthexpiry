import pytest

from truthexpiry.services.claim_key import (
    build_claim_key,
    normalize_token,
    parse_canonical_key,
)


def test_normalize_token():
    assert normalize_token(" Report Export ") == "report_export"


def test_build_claim_key_canonical():
    key = build_claim_key(
        "Report Export",
        "Availability",
        {"Region": "Global", "Plan": "Starter"},
    )
    assert key.canonical() == "report_export|availability|plan=starter|region=global"


def test_build_claim_key_omits_empty_scope_values():
    key = build_claim_key("entity", "attribute", {"plan": "starter", "region": ""})
    assert key.canonical() == "entity|attribute|plan=starter"


def test_parse_canonical_key_roundtrip():
    original = build_claim_key("api_rate_limit", "max_requests", {"plan": "starter"})
    restored = parse_canonical_key(original.canonical())
    assert restored == original


def test_parse_canonical_key_invalid():
    with pytest.raises(ValueError, match="Invalid claim key"):
        parse_canonical_key("only-one-part")

    with pytest.raises(ValueError, match="Invalid scope fragment"):
        parse_canonical_key("entity|attribute|badfragment")
