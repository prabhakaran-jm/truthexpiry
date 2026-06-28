from datetime import date

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.evidence import LifecycleRecord, LifecycleState
from truthexpiry.models.verdict import ClaimStatus, OwnerConfirmation
from truthexpiry.services.claim_key import build_claim_key
from truthexpiry.services.labeler import label_claim

from adapters.fakes.synthetic_data import BILLING_REFUND_KEY, LIFECYCLE_RECORDS

ON_DATE = date(2024, 6, 15)
OWNER_ID = "U_OWNER"
OTHER_USER_ID = "U_OTHER"


def test_owner_can_confirm_unverified_claim_without_active_authority():
    key = build_claim_key(
        "custom_widget", "availability", {"plan": "starter", "region": "global"}
    )
    claim = ExtractedClaim(
        key=key,
        stated_value="beta",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(
        claim,
        [],
        on_date=ON_DATE,
        entity_owners={key.entity: OWNER_ID},
        owner_confirmations=(
            OwnerConfirmation(
                entity=key.entity,
                owner_user_id=OWNER_ID,
                confirmed_by_user_id=OWNER_ID,
            ),
        ),
    )
    assert result.status is ClaimStatus.UNVERIFIED
    assert result.user_confirmed is True
    assert result.lifecycle_record_ids == ()


def test_non_owner_cannot_confirm_claim():
    key = build_claim_key(
        "custom_widget", "availability", {"plan": "starter", "region": "global"}
    )
    claim = ExtractedClaim(
        key=key,
        stated_value="beta",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(
        claim,
        [],
        on_date=ON_DATE,
        entity_owners={key.entity: OWNER_ID},
        owner_confirmations=(
            OwnerConfirmation(
                entity=key.entity,
                owner_user_id=OWNER_ID,
                confirmed_by_user_id=OTHER_USER_ID,
            ),
        ),
    )
    assert result.status is ClaimStatus.UNVERIFIED
    assert result.user_confirmed is False
    assert (
        "No matching authoritative lifecycle evidence was found" in result.explanation
    )


def test_owner_confirmation_cannot_override_contradictory_active_record():
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
    claim = ExtractedClaim(
        key=key,
        stated_value="enabled",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(
        claim,
        records,
        on_date=ON_DATE,
        entity_owners={key.entity: OWNER_ID},
        owner_confirmations=(
            OwnerConfirmation(
                entity=key.entity,
                owner_user_id=OWNER_ID,
                confirmed_by_user_id=OWNER_ID,
            ),
        ),
    )
    assert result.status is ClaimStatus.SUPERSEDED
    assert result.user_confirmed is False
    assert result.lifecycle_record_ids == ("LC-SYNTH-040",)


def test_owner_confirmation_does_not_resolve_conflicting_records():
    claim = ExtractedClaim(
        key=BILLING_REFUND_KEY,
        stated_value="30_days",
        required_scope_fields=("plan", "region"),
    )
    result = label_claim(
        claim,
        LIFECYCLE_RECORDS[BILLING_REFUND_KEY.canonical()],
        on_date=ON_DATE,
        entity_owners={BILLING_REFUND_KEY.entity: OWNER_ID},
        owner_confirmations=(
            OwnerConfirmation(
                entity=BILLING_REFUND_KEY.entity,
                owner_user_id=OWNER_ID,
                confirmed_by_user_id=OWNER_ID,
            ),
        ),
    )
    assert result.status is ClaimStatus.CONFLICTING
    assert result.user_confirmed is False
