from dataclasses import dataclass
from datetime import date
from enum import Enum

from truthexpiry.models.claim import ClaimKey


class LifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    PLANNED = "PLANNED"
    SHIPPED = "SHIPPED"
    EFFECTIVE = "EFFECTIVE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"


AUTHORITATIVE_STATES = frozenset({LifecycleState.SHIPPED, LifecycleState.EFFECTIVE})
INACTIVE_STATES = frozenset(
    {
        LifecycleState.PROPOSED,
        LifecycleState.PLANNED,
        LifecycleState.CANCELLED,
        LifecycleState.REJECTED,
        LifecycleState.DRAFT,
    }
)


@dataclass(frozen=True)
class LifecycleRecord:
    record_id: str
    key: ClaimKey
    state: LifecycleState
    value: str
    effective_date: date
    supersedes_record_id: str | None = None

    def is_authoritative_on(self, on_date: date) -> bool:
        return self.state in AUTHORITATIVE_STATES and self.effective_date <= on_date
