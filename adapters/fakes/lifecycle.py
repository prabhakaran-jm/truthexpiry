from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord

from adapters.fakes.synthetic_data import LIFECYCLE_RECORDS


class FakeLifecycleEvidenceAdapter:
    """In-process lifecycle evidence with synthetic Jira-like records."""

    def __init__(self, records: dict[str, list[LifecycleRecord]] | None = None) -> None:
        self._records = records if records is not None else LIFECYCLE_RECORDS
        self.fetch_calls: list[str] = []

    def fetch_records(self, key: ClaimKey) -> list[LifecycleRecord]:
        canonical = key.canonical()
        self.fetch_calls.append(canonical)
        stored = self._records.get(canonical, [])
        return list(stored)
