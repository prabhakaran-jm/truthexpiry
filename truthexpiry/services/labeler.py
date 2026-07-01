from datetime import date

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.evidence import (
    AUTHORITATIVE_STATES,
    INACTIVE_STATES,
    LifecycleRecord,
)
from truthexpiry.models.verdict import (
    ClaimStatus,
    LifecycleTimelineEntry,
    OwnerConfirmation,
    ValidationResult,
)
from truthexpiry.services.lifecycle_timeline import build_timeline_entries


def _timeline(records: list[LifecycleRecord]) -> tuple[LifecycleTimelineEntry, ...]:
    return build_timeline_entries(records)


def _active_authoritative(
    records: list[LifecycleRecord], on_date: date
) -> list[LifecycleRecord]:
    return [record for record in records if record.is_authoritative_on(on_date)]


def _future_effective_authoritative(
    records: list[LifecycleRecord], on_date: date
) -> list[LifecycleRecord]:
    return [
        record
        for record in records
        if record.state in AUTHORITATIVE_STATES and record.effective_date > on_date
    ]


def _distinct_values(records: list[LifecycleRecord]) -> set[str]:
    return {record.value for record in records}


def _find_superseding_record(
    claim: ExtractedClaim,
    active_records: list[LifecycleRecord],
) -> LifecycleRecord | None:
    if not active_records:
        return None

    matched_records = [
        record for record in active_records if record.value == claim.stated_value
    ]
    for matched in matched_records:
        for candidate in active_records:
            if (
                candidate.supersedes_record_id == matched.record_id
                and candidate.value != claim.stated_value
            ):
                return candidate

    if matched_records:
        return None

    latest = max(
        active_records,
        key=lambda record: (record.effective_date, record.record_id),
    )
    if latest.value != claim.stated_value and latest.supersedes_record_id:
        return latest
    return None


def _has_unresolved_conflict(active_records: list[LifecycleRecord]) -> bool:
    if len(active_records) < 2 or len(_distinct_values(active_records)) < 2:
        return False

    for left in active_records:
        for right in active_records:
            if left.record_id == right.record_id:
                continue
            if left.value == right.value:
                continue
            if right.supersedes_record_id == left.record_id:
                continue
            if left.supersedes_record_id == right.record_id:
                continue
            return True
    return False


def _active_records_contradict_claim(
    claim: ExtractedClaim, active_records: list[LifecycleRecord]
) -> bool:
    if not active_records:
        return False
    distinct_values = _distinct_values(active_records)
    return len(distinct_values) == 1 and claim.stated_value not in distinct_values


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
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
        )

    active = _active_authoritative(records, on_date)
    inactive = [record for record in records if record.state in INACTIVE_STATES]
    future_effective = _future_effective_authoritative(records, on_date)

    superseding = _find_superseding_record(claim, active)
    if superseding is not None:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.SUPERSEDED,
            explanation=(
                "A later authoritative lifecycle record supersedes the value stated "
                "in Slack evidence."
            ),
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=(superseding.record_id,),
            lifecycle_timeline=_timeline(records),
        )

    if _has_unresolved_conflict(active):
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.CONFLICTING,
            explanation="Multiple active authoritative lifecycle records disagree for this claim key.",
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in active),
            lifecycle_timeline=_timeline(records),
        )

    matching = [record for record in active if record.value == claim.stated_value]
    if matching:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.CURRENT,
            explanation="An authoritative lifecycle record matches this claim's value and scope.",
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in matching),
            lifecycle_timeline=_timeline(records),
        )

    if _active_records_contradict_claim(claim, active):
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.SUPERSEDED,
            explanation=(
                "The claim conflicts with the current authoritative lifecycle state."
            ),
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in active),
            lifecycle_timeline=_timeline(records),
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
                    stated_value=claim.stated_value,
                    evidence_refs=claim.evidence_refs,
                    user_confirmed=True,
                )

    if inactive and not active:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.UNVERIFIED,
            explanation="Lifecycle evidence exists but is not yet authoritative.",
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in inactive),
            lifecycle_timeline=_timeline(records),
        )

    if future_effective and not active:
        return ValidationResult(
            key=claim.key,
            status=ClaimStatus.UNVERIFIED,
            explanation=(
                "Authoritative lifecycle evidence exists but has not taken effect yet."
            ),
            stated_value=claim.stated_value,
            evidence_refs=claim.evidence_refs,
            lifecycle_record_ids=tuple(record.record_id for record in future_effective),
            lifecycle_timeline=_timeline(records),
        )

    return ValidationResult(
        key=claim.key,
        status=ClaimStatus.UNVERIFIED,
        explanation="No matching authoritative lifecycle evidence was found.",
        stated_value=claim.stated_value,
        evidence_refs=claim.evidence_refs,
    )
