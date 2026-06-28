from typing import Protocol

from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord


class LifecycleEvidenceUnavailableError(RuntimeError):
    """Raised when authoritative lifecycle evidence cannot be retrieved."""


class LifecycleEvidencePort(Protocol):
    def fetch_records(self, key: ClaimKey) -> list[LifecycleRecord]: ...
