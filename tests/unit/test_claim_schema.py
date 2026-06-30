import pytest

from truthexpiry.services.claim_schema import CLAIM_SCHEMA_CATALOG, lookup_claim_schema
from truthexpiry.services.claim_key import normalize_token


@pytest.mark.parametrize(
    ("entity", "attribute", "values"),
    [
        ("report_export", "availability", {"enabled", "disabled"}),
        ("analytics_export", "availability", {"enabled"}),
        ("api_rate_limit", "max_requests", {"100", "50"}),
        ("billing_refund", "policy", {"30_days", "60_days"}),
        ("mobile_push", "delivery", {"enabled"}),
        ("feature_flag", "rollout", {"enabled"}),
        ("legacy_api", "sunset", {"deprecated"}),
    ],
)
def test_catalog_contains_supported_pairs(entity, attribute, values):
    schema = lookup_claim_schema(entity, attribute)
    assert schema is not None
    assert schema.allowed_stated_values == frozenset(values)
    assert schema.required_scope_keys == frozenset({"plan", "region"})
    assert dict(schema.scope_defaults) == {"region": "global"}


def test_catalog_is_immutable_mapping():
    with pytest.raises(TypeError):
        CLAIM_SCHEMA_CATALOG[(normalize_token("x"), normalize_token("y"))] = None  # type: ignore[index]


def test_unsupported_pair_returns_none():
    assert lookup_claim_schema("unknown", "feature") is None
