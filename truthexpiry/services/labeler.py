from datetime import date

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.evidence import INACTIVE_STATES, LifecycleRecord
from truthexpiry.models.verdict import ClaimStatus, OwnerConfirmation, ValidationResult


def _active_authoritative(
    records: list[LifecycleRecord], on_date: date
) -> list[LifecycleRecord]:
    return [record for record in records if record.is_authoritative_on(on_date)]


def _distinct_values(records: list[LifecycleRecord]) -> set[str]:
    return {record.value for record in records}


def _latest_by_effective_date(records: list[LifecycleRecord]) -> LifecycleRecord | None:
    if not records:
        return None
    return max(records, key=lambda record: (record.effective_date, record.record_id))


def _is_superseded_by(
    claim: ExtractedClaim,
    active_records: list[LifecycleRecord],
    on_date: date,
) -> LifecycleRecord | None:
    matching_value = [
        record for record in active_records if record.value == claim.stated_value
    ]
    if matching_value:
        return None

    conflicting = [
        record for record in active_records if record.value != claim.stated_value
    ]
    if not conflicting:
        return None

    latest = _latest_by_effective_date(conflicting)
    if latest is None:
        return None

    for record in conflicting:
        if record.supersedes_record_id and record.value != claim.stated_value:
            return latest

    if latest.effective_date <= on_date and latest.value != claim.stated_value:
        return latest

    return None


def label_claim(
    claim: ExtractedClaim,
    records: list[LifecycleRecord],
    *,
    on_date: date,
    owner_confirmations: tuple[OwnerConfirmation, ...] = (),
    entity_owners: dict[str, str] | None = None,
) -> ValidationResult:
    entity_owners = entity_owners or {}

    if not claim.key.scope.is_complete(claim.required_scope_fields):
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.UNVERIFIED,
            explanation="Required scope fields are missing for this claim.",
            evidence_refs=claim.evidence_refs,
        )

    active = _active_authoritative(records, on_date)
    inactive = [record for record in records if record.state in INACTIVE_STATES]

    if len(active) >= 2 and len(_distinct_values(active)) > 1:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.CONFLICTING,
            explanation="Multiple active authoritative lifecycle records disagree for this claim key.",
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in active),
        )

    matching = [record for record in active if record.value == claim.stated_value]
    if matching and len(_distinct_values(active)) == 1:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.CURRENT,
            explanation="An authoritative lifecycle record matches this claim's value and scope.",
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in matching),
        )

    superseding = _is_superseded_by(claim, active, on_date)
    if superseding is not None:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.SUPERSEDED,
            explanation=(
                "A later authoritative lifecycle record supersedes the value stated in Slack evidence."
            ),
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=(superseding.record_id,),
        )

    configured_owner = entity_owners.get(claim.key.entity)
    if configured_owner:
        for confirmation in owner_confirmations:
            if (
                confirmation.entity == claim.key.entity
                and confirmation.confirmed_by_user_id == configured_owner
                and not active
            ):
                return ValidationResult(
                    key=claim.key,
                    status=ClaimStatus.UNVERIFIED,
                    explanation="Owner confirmed this claim pending authoritative lifecycle evidence.",
                    evidence_refs=claim.evidence_refs,
                    user_confirmed=True,
                )

    if inactive and not active:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.UNVERIFIED,
            explanation="Lifecycle evidence exists but is not yet authoritative.",
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in inactive),
        )

    return ValidationResult(
        key=claim.key,
        status=ClaimStatus.UNVERIFIED,
        explanation="No matching authoritative lifecycle evidence was found.",
        evidence_refs=claim.evidence_refs,
    )
