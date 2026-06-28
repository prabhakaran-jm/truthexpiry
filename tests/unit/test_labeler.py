from datetime import date

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.evidence import LifecycleRecord, LifecycleState
from truthexpiry.models.verdict import ClaimStatus
from truthexpiry.services.claim_key import build_claim_key
from truthexpiry.services.labeler import label_claim

from adapters.fakes.synthetic_data import (
    ANALYTICS_EXPORT_KEY,
    API_RATE_LIMIT_KEY,
    BILLING_REFUND_KEY,
    FEATURE_FLAG_KEY,
    LIFECYCLE_RECORDS,
    PLANNED_ONLY_KEY,
)

ON_DATE = date(2024, 6, 15)


def _claim(key, value: str) -> ExtractedClaim:
    return ExtractedClaim(
        key=key,
        stated_value=value,
        required_scope_fields=("plan", "region"),
    )


def test_label_current_when_lifecycle_matches():
    result = label_claim(
        _claim(ANALYTICS_EXPORT_KEY, "enabled"),
        LIFECYCLE_RECORDS[ANALYTICS_EXPORT_KEY.canonical()],
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.CURRENT


def test_label_superseded_when_later_record_replaces_value():
    result = label_claim(
        _claim(API_RATE_LIMIT_KEY, "100"),
        LIFECYCLE_RECORDS[API_RATE_LIMIT_KEY.canonical()],
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.SUPERSEDED
    assert result.lifecycle_record_ids == ("PROD-511",)


def test_label_conflicting_when_dual_authority_disagrees():
    result = label_claim(
        _claim(BILLING_REFUND_KEY, "30_days"),
        LIFECYCLE_RECORDS[BILLING_REFUND_KEY.canonical()],
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.CONFLICTING
    assert len(result.lifecycle_record_ids) == 2


def test_label_unverified_when_only_inactive_evidence():
    result = label_claim(
        _claim(PLANNED_ONLY_KEY, "enabled"),
        LIFECYCLE_RECORDS[PLANNED_ONLY_KEY.canonical()],
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.UNVERIFIED
    assert "not yet authoritative" in result.explanation


def test_label_unverified_when_scope_incomplete():
    incomplete_key = build_claim_key(
        "report_export", "availability", {"plan": "starter"}
    )
    claim = ExtractedClaim(
        key=incomplete_key,
        stated_value="self_serve",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(claim, [], on_date=ON_DATE)
    assert result.status is ClaimStatus.UNVERIFIED
    assert "scope" in result.explanation.lower()


def test_label_unverified_when_no_lifecycle_records():
    orphan_key = build_claim_key(
        "unknown", "feature", {"plan": "starter", "region": "global"}
    )
    claim = ExtractedClaim(
        key=orphan_key,
        stated_value="enabled",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(claim, [], on_date=ON_DATE)
    assert result.status is ClaimStatus.UNVERIFIED


def test_supersession_requires_lifecycle_not_message_timestamps():
    """A later SHIPPED record with explicit supersedes link drives SUPERSEDED."""
    key = build_claim_key("demo", "flag", {"env": "prod"})
    records = [
        LifecycleRecord(
            record_id="LC-OLD",
            key=key,
            state=LifecycleState.EFFECTIVE,
            value="on",
            effective_date=date(2024, 1, 1),
        ),
        LifecycleRecord(
            record_id="LC-NEW",
            key=key,
            state=LifecycleState.SHIPPED,
            value="off",
            effective_date=date(2024, 2, 1),
            supersedes_record_id="LC-OLD",
        ),
    ]
    result = label_claim(
        ExtractedClaim(key=key, stated_value="on", required_scope_fields=("env",)),
        records,
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.SUPERSEDED


def test_single_active_authoritative_record_supersedes_claim():
    key = build_claim_key(
        "mobile_push", "delivery", {"plan": "starter", "region": "global"}
    )
    records = [
        LifecycleRecord(
            record_id="LC-SYNTH-040",
            key=key,
            state=LifecycleState.SHIPPED,
            value="disabled",
            effective_date=date(2024, 1, 1),
        ),
    ]
    result = label_claim(
        ExtractedClaim(
            key=key,
            stated_value="enabled",
            required_scope_fields=("plan", "region"),
        ),
        records,
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.SUPERSEDED
    assert result.lifecycle_record_ids == ("LC-SYNTH-040",)
    assert (
        "conflicts with the current authoritative lifecycle state" in result.explanation
    )
    assert (
        "No matching authoritative lifecycle evidence was found"
        not in result.explanation
    )


def test_label_unverified_when_only_future_effective_record():
    records = LIFECYCLE_RECORDS[FEATURE_FLAG_KEY.canonical()]
    result = label_claim(
        ExtractedClaim(
            key=FEATURE_FLAG_KEY,
            stated_value="enabled",
            required_scope_fields=("plan", "region"),
        ),
        records,
        on_date=ON_DATE,
    )
    assert result.status is ClaimStatus.UNVERIFIED
    assert result.lifecycle_record_ids == ("PROD-530",)
    assert "has not taken effect yet" in result.explanation
    assert (
        "No matching authoritative lifecycle evidence was found"
        not in result.explanation
    )
