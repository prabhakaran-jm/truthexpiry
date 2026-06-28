from dataclasses import dataclass
from enum import Enum

from truthexpiry.models.claim import ClaimKey, EvidenceRef


class ClaimStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


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
    evidence_refs: tuple[EvidenceRef, ...] = ()
    lifecycle_record_ids: tuple[str, ...] = ()
    user_confirmed: bool = False
