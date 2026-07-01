from dataclasses import dataclass
from datetime import date
from enum import Enum

from truthexpiry.models.claim import ClaimKey, EvidenceRef


class ClaimStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class LifecycleTimelineEntry:
    record_id: str
    value: str
    effective_date: date
    state: str
    supersedes_record_id: str | None = None


@dataclass(frozen=True)
class OwnerConfirmation:
    entity: str
    owner_user_id: str
    confirmed_by_user_id: str


@dataclass(frozen=True)
class ValidationResult:
    key: ClaimKey
    status: ClaimStatus
    explanation: str
    stated_value: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    lifecycle_record_ids: tuple[str, ...] = ()
    lifecycle_timeline: tuple[LifecycleTimelineEntry, ...] = ()
    user_confirmed: bool = False
