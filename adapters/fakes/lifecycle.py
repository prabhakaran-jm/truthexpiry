from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord

from adapters.fakes.synthetic_data import LIFECYCLE_RECORDS
from lifecycle_mcp.repository import LifecycleRecordRepository, default_repository


class FakeLifecycleEvidenceAdapter:
    """In-process lifecycle evidence with synthetic Jira-like records."""

    def __init__(
        self,
        records: dict[str, list[LifecycleRecord]] | None = None,
        repository: LifecycleRecordRepository | None = None,
    ) -> None:
        self._repository = repository or default_repository()
        self._records = records if records is not None else LIFECYCLE_RECORDS
        self.fetch_calls: list[str] = []

    def fetch_records(self, key: ClaimKey) -> list[LifecycleRecord]:
        canonical = key.canonical()
        self.fetch_calls.append(canonical)
        if self._records is LIFECYCLE_RECORDS:
            return self._repository.find_domain_records(key)
        stored = self._records.get(canonical, [])
        return list(stored)
